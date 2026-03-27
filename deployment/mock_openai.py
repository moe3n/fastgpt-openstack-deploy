import http.server
import json
import hashlib
import math
import re

class MockOpenAIHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/v1/models'):
            self.send_json({"object": "list", "data": [
                {"id": "gpt-3.5-turbo", "object": "model"},
                {"id": "text-embedding-ada-002", "object": "model"}
            ]})
        else:
            self.send_json({"object": "list", "data": []})

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        path = self.path.split('?')[0]

        if path == '/v1/embeddings':
            inputs = body.get('input', '')
            if isinstance(inputs, str):
                inputs = [inputs]
            embeddings = []
            for i, text in enumerate(inputs):
                vec = self._text_to_vector(str(text), 1536)
                embeddings.append({"object": "embedding", "index": i, "embedding": vec})
            self.send_json({
                "object": "list",
                "data": embeddings,
                "model": body.get('model', 'text-embedding-ada-002'),
                "usage": {"prompt_tokens": 10, "total_tokens": 10}
            })

        elif path == '/v1/chat/completions':
            messages = body.get('messages', [])
            user_msg = next((m['content'] for m in reversed(messages) if m.get('role') == 'user'), '')
            # FastGPT injects retrieved KB chunks into the system message
            sys_msg = next((m['content'] for m in messages if m.get('role') == 'system'), '')

            # FastGPT v4.14.9 wraps retrieved KB chunks in <Cites><Cite id="N">...</Cite></Cites>
            # Everything outside these tags is Chinese boilerplate — ignore it.
            context_lines = []
            cite_blocks = re.findall(r'<Cite(?!\w)[^>]*>(.*?)</Cite>', sys_msg, re.DOTALL)
            for block in cite_blocks:
                for line in block.splitlines():
                    stripped = line.strip()
                    if stripped.lower().startswith('a:'):
                        context_lines.append(stripped[2:].strip())
                    elif stripped and not stripped.lower().startswith('q:'):
                        context_lines.append(stripped)

            if context_lines:
                context_excerpt = ' '.join(context_lines[:3])[:600]
                reply = (
                    f"Based on the knowledge base, here is what I found about "
                    f"\"{user_msg[:100]}\":\n\n"
                    f"{context_excerpt}\n\n"
                    f"(Response grounded in retrieved KB context.)"
                )
            else:
                reply = (
                    f"I could not find specific information about \"{user_msg[:150]}\" "
                    f"in the knowledge base. Please ensure relevant documents have been "
                    f"uploaded and the embedding model is active."
                )

            stream = body.get('stream', False)
            if stream:
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.end_headers()
                chunk = {"id":"mock-1","object":"chat.completion.chunk","choices":[{"delta":{"role":"assistant","content":reply},"index":0,"finish_reason":None}]}
                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
                done = {"id":"mock-1","object":"chat.completion.chunk","choices":[{"delta":{},"index":0,"finish_reason":"stop"}]}
                self.wfile.write(f"data: {json.dumps(done)}\n\ndata: [DONE]\n\n".encode())
            else:
                self.send_json({
                    "id": "mock-chatcmpl-1",
                    "object": "chat.completion",
                    "model": body.get('model', 'gpt-3.5-turbo'),
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": reply}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 50, "completion_tokens": 50, "total_tokens": 100}
                })
        else:
            self.send_json({"object": "list", "data": []})

    def _text_to_vector(self, text, dim):
        # Deterministic hash-based embedding — same text always gives same vector
        vec = []
        seed = text.encode('utf-8')
        for i in range(dim):
            h = hashlib.sha256(seed + i.to_bytes(4, 'big')).digest()
            val = int.from_bytes(h[:4], 'big') / 0xFFFFFFFF * 2 - 1
            vec.append(val)
        # Normalize to unit vector
        norm = math.sqrt(sum(v*v for v in vec))
        return [v / norm for v in vec] if norm > 0 else vec

    def send_json(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass

http.server.HTTPServer(('0.0.0.0', 3002), MockOpenAIHandler).serve_forever()
