# Django Channels & Setup Guide

## What is Django Channels?

Django Channels extends Django's capabilities beyond HTTP to support:

- WebSockets  
- Chat protocols  
- IoT and custom async protocols  

It adds support for both **synchronous and asynchronous** views and works with:

- Django authentication (`self.scope["user"]`)  
- Session management  
- Django models and middleware  

**Use case examples:** Live chat, real-time dashboards, notification systems, multiplayer games.

---

## Project Setup Steps

### Step 1: Create a Django Project

```bash
django-admin startproject myproject
cd myproject
```

Or with virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install django
django-admin startproject myproject .
```

---

### Step 2: Install Django Channels

```bash
pip install channels
```

---

### Step 3: Update `settings.py`

```python
INSTALLED_APPS = [
    'channels',
    # other apps
]

ASGI_APPLICATION = 'myproject.asgi.application'
```

---

## ASGI Application Configuration (`asgi.py`)

### What is `asgi.py`?

`asgi.py` is the **entry point for your Django project** when running under an **ASGI (Asynchronous Server Gateway Interface)** server, such as:

- Uvicorn  
- Daphne  
- Hypercorn

It serves a similar role to `wsgi.py` but is designed to support **asynchronous communication**, including:

- WebSockets  
- HTTP/2  
- Background tasks  

### Role in Django Channels

When using **Django Channels**, `asgi.py` becomes responsible for:

- Receiving all incoming **HTTP and WebSocket** connections  
- Routing based on **protocol type** (`http`, `websocket`, etc.)  
- Injecting middleware like authentication  
- Mapping WebSocket paths to consumers  

Basic setup:

```python
from channels.routing import ProtocolTypeRouter
from django.core.asgi import get_asgi_application

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    # Add "websocket" config later
})
```

To support WebSocket connections, extend like this:

```python
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import app.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(app.routing.websocket_urlpatterns)
    ),
})
```

### Component Breakdown

- **`from django.core.asgi import get_asgi_application`**: Returns Django's default HTTP ASGI handler. Handles standard HTTP views, APIs, etc.
- **`from channels.routing import ProtocolTypeRouter, URLRouter`**: `ProtocolTypeRouter` routes connections by type (`http`, `websocket`, etc.). `URLRouter` matches WebSocket paths to consumer classes.
- **`from channels.auth import AuthMiddlewareStack`**: Adds session and user authentication to WebSocket connections. Enables `self.scope["user"]` in consumers.
- **`import app.routing`**: Imports your app's `routing.py` which defines `websocket_urlpatterns`.
- **`os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')`**: Points Django to your project's settings module. Required before initializing the application.
- **`application = ProtocolTypeRouter({...})`**: The ASGI entry point. Routes different protocols to appropriate handlers.
- **`"http": get_asgi_application()`**: Handles all traditional HTTP requests. Equivalent to `wsgi.py` logic.
- **`"websocket": AuthMiddlewareStack(...)`**: Handles all WebSocket requests: Applies authentication/session middleware, Routes to WebSocket consumers via `URLRouter`

### Request Flow Through `asgi.py`

```text
Client Browser ──▶ ASGI Server (e.g., Uvicorn)
                 └─▶ asgi.py:
                     ├── "http"      → Django view (via get_asgi_application)
                     └── "websocket" → AuthMiddlewareStack
                                         └── URLRouter
                                             └── WebSocket Consumer
```

---

## WSGI vs ASGI — What's the Difference?

### Feature Comparison Table

| Feature                    | WSGI (Web Server Gateway Interface)                  | ASGI (Asynchronous Server Gateway Interface)         |
|----------------------------|------------------------------------------------------|------------------------------------------------------|
| Purpose                    | Interface for synchronous Python web apps           | Successor to WSGI; supports asynchronous protocols   |
| Protocol Support           | HTTP only                                            | HTTP, WebSocket, HTTP/2, SSE, Lifespan               |
| Communication Type         | Half-duplex (request → response → done)             | Full-duplex (2-way, real-time communication)         |
| Concurrency Model          | Synchronous (thread/block-based)                    | Asynchronous (event-loop with `await`)               |
| WebSocket Support          | ❌ Not supported                                     | ✅ Fully supported                                   |
| Real-Time Support          | ❌ No                                                | ✅ Yes (chat, notifications, IoT, etc.)              |
| Execution Type             | Blocking I/O                                        | Non-blocking async I/O                               |
| Deployment Stack           | Gunicorn, uWSGI, mod_wsgi                           | Uvicorn, Daphne, Hypercorn                           |
| Typical Use Cases          | Blogs, admin panels, e-commerce, REST APIs          | Chat apps, games, real-time dashboards, live feeds   |
| Default Django File        | `wsgi.py`                                           | `asgi.py`                                            |

### Code Comparison

#### `wsgi.py` — Traditional (HTTP-only)

```python
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
application = get_wsgi_application()
```

- Used in standard Django apps
- Compatible with Gunicorn, uWSGI, mod_wsgi
- Handles only synchronous HTTP requests

#### `asgi.py` — Async + WebSocket (Django Channels)

```python
import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
import app.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(app.routing.websocket_urlpatterns)
    ),
})
```

- Handles HTTP and WebSocket
- Works with async servers like Uvicorn, Daphne
- Routes WebSocket connections to consumers

### Real-World Use Case Comparison

| Use Case                     | WSGI Supported | ASGI Supported |
|-----------------------------|----------------|----------------|
| Admin panel (Django)         | ✅ Yes          | ✅ Yes          |
| REST API                     | ✅ Yes          | ✅ Yes          |
| WebSocket chat app           | ❌ No           | ✅ Yes          |
| Real-time stock ticker       | ❌ No           | ✅ Yes          |
| IoT dashboard (device pings) | ❌ No           | ✅ Yes          |
| Multiplayer game server      | ❌ No           | ✅ Yes          |
| Background async tasks       | ❌ Workarounds  | ✅ Native       |

### When to Use WSGI vs ASGI

#### Use WSGI if you only need:

- Static pages
- Form submissions
- Admin interface
- Simple REST APIs

#### Use ASGI if you need:

- WebSockets
- Live notifications
- Realtime dashboards
- IoT or sensor streams
- Concurrent tasks (`async def`)
- Long-lived connections

---

## WebSocket Routing

### `app/routing.py`

In Django Channels, `routing.py` serves the same purpose as `urls.py`, **but for WebSocket connections**.

While `urls.py` maps HTTP paths to Django views,  
**`routing.py` maps WebSocket paths to consumer classes**.

```python
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/chat/', consumers.MySyncConsumer.as_asgi()),
]
```

### What is an ASGI App?

**Definition:** An ASGI app is a callable (i.e., something Python can call like a function) that handles ASGI connections (such as HTTP, WebSocket, or lifespan events). It follows the ASGI protocol and communicates using three components:

```python
async def app(scope, receive, send):
    # scope → connection metadata (type, path, headers, user, etc.)
    # receive() → gets messages/events from the client (e.g., HTTP request or WebSocket frame)
    # send() → sends responses or messages back to the client
```

When you write:
```python
path("ws/chat/", consumers.ChatConsumer.as_asgi())
```

It means:
1. You're creating a route for WebSocket connections at `/ws/chat/`.
2. `ChatConsumer.as_asgi()` converts your ChatConsumer class into a valid ASGI application — that is, it returns a callable `app(scope, receive, send)`.
3. When a client connects to `/ws/chat/`, Django Channels:
   - Calls that `as_asgi()` function.
   - Creates a new instance of the consumer class (ChatConsumer) for each WebSocket connection.
   - Passes the connection scope, and handles `receive()`/`send()` via the consumer.

### What Happens on a Request

When a browser sends:

```js
const socket = new WebSocket("ws://localhost:8000/ws/chat/");
```

Django Channels internally does the following:

1. `asgi.py` receives the request  
2. Recognizes it as a WebSocket protocol  
3. Passes it through `AuthMiddlewareStack`  
4. Routes it using `URLRouter(websocket_urlpatterns)`  
5. Matches the path `/ws/chat/`  
6. Instantiates `ChatConsumer`  
7. Triggers these methods based on events:
   - `websocket_connect()`
   - `websocket_receive()`
   - `websocket_disconnect()`

### Example with Multiple Routes

```python
websocket_urlpatterns = [
    path("ws/chat/", consumers.ChatConsumer.as_asgi()),
    path("ws/notify/", consumers.NotificationConsumer.as_asgi()),
    path("ws/live/", consumers.LiveFeedConsumer.as_asgi()),
]
```

### Add WebSocket Routing to `asgi.py`

```python
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
import app.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": URLRouter(app.routing.websocket_urlpatterns)
})
```

---

## Creating Consumers

A **consumer** in Django Channels is a Python class that handles WebSocket lifecycle events.  
It is similar to Django views, but specifically designed for **persistent, two-way WebSocket communication**.

### Difference Between AsyncWebsocketConsumer and AsyncConsumer

| Feature | AsyncWebsocketConsumer | AsyncConsumer / SyncConsumer |
|---------|------------------------|------------------------------|
| ✅ Purpose | Built-in support for WebSocket-specific events | Low-level ASGI event handler (works with any ASGI protocol) |
| 🧠 Event Dispatch | Internally maps WebSocket events to class methods | You must handle raw ASGI event names manually ("websocket.receive") |
| 📥 Receive Method Name | `async def receive(self, text_data=None)` | `async def websocket_receive(self, event)` |
| 🔌 Connection Handling | `connect()`, `receive()`, `disconnect()` | `websocket_connect()`, `websocket_receive()`, `websocket_disconnect()` |
| 🧰 Abstraction Level | High — easier for WebSocket-only use cases | Low — flexible for other protocols (e.g., HTTP, lifespan) |
| 🛠️ Auto-handles accept/close | Yes — e.g., `await self.accept()` | No — must send raw ASGI messages (`type: websocket.accept`) |
| 💬 Built-in send() | `await self.send(text_data="...")` | `await self.send({"type": "websocket.send", "text": "..."})` |
| 🧪 Best Use Case | When you're building WebSocket-only features like chats, games | When you're building a low-level ASGI app with custom protocol handling |

### Example: AsyncWebsocketConsumer (High-Level)

```python
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def receive(self, text_data=None):
        await self.send(text_data=f"You said: {text_data}")

    async def disconnect(self, close_code):
        print("Disconnected")
```

No need to manage ASGI message types — Django handles it.

### Example: AsyncConsumer (Low-Level)

```python
from channels.consumer import AsyncConsumer

class ChatConsumer(AsyncConsumer):
    async def websocket_connect(self, event):
        await self.send({"type": "websocket.accept"})

    async def websocket_receive(self, event):
        message = event["text"]
        await self.send({
            "type": "websocket.send",
            "text": f"You said: {message}"
        })

    async def websocket_disconnect(self, event):
        print("Disconnected")
```

You handle ASGI event names directly.

### Example: Synchronous Consumer

```python
from channels.consumer import SyncConsumer
from channels.exceptions import StopConsumer

class MySyncConsumer(SyncConsumer):
    def websocket_connect(self, event):
        self.send({"type": "websocket.accept"})

    def websocket_receive(self, event):
        self.send({
            "type": "websocket.send",
            "text": f"You said: {event['text']}"
        })

    def websocket_disconnect(self, event):
        raise StopConsumer()
```

### Which One Should You Use?

| You Should Use | If... |
|----------------|-------|
| AsyncWebsocketConsumer | You're building a WebSocket-only app (chat, notifications, real-time dashboards). Easier and more readable. |
| AsyncConsumer | You need full control over ASGI events, want to support multiple protocols (e.g., HTTP + WebSocket), or need custom message handling. |

---

## WebSocket Lifecycle Events

### Basic Lifecycle Events

A WebSocket consumer typically responds to these events:

| Event                        | Method in Consumer               |
|-----------------------------|----------------------------------|
| `websocket.connect`         | `websocket_connect(self, event)` |
| `websocket.receive`         | `websocket_receive(self, event)` |
| `websocket.disconnect`      | `websocket_disconnect(self, event)` |

### Automatic Event Binding

Django Channels uses method names to bind WebSocket events automatically:

- `"websocket.connect"` → `websocket_connect(self, event)`
- `"websocket.receive"` → `websocket_receive(self, event)`
- `"websocket.disconnect"` → `websocket_disconnect(self, event)`

There is **no need for manual dispatching** — the method name is enough.

### WebSocket Event Types

#### 1. `websocket.connect` (Client → Server)

Triggered when a client initiates a connection.

```json
{
  "type": "websocket.connect"
}
```

**Accept the connection:**

```python
self.send({
    "type": "websocket.accept"
})
```

**With headers (e.g., to set cookies):**

```python
self.send({
    "type": "websocket.accept",
    "headers": [[b"set-cookie", b"sessionid=xyz"]]
})
```

#### 2. `websocket.receive` (Client → Server)

Triggered when the client sends data.

```json
{
  "type": "websocket.receive",
  "text": "Hello",
  "bytes": null
}
```

**Echo example:**

```python
self.send({
    "type": "websocket.send",
    "text": f"You said: {event['text']}"
})
```

#### 3. `websocket.send` (Server → Client)

Used by the server to send a message to the client.

```json
{
  "type": "websocket.send",
  "text": "Hello from server!"
}
```

**Typical use cases:**

- Real-time chat  
- Notifications  
- Live dashboards  

#### 4. `websocket.disconnect` (Client/Server → Server)

Triggered when the connection closes (intentionally or by error).

```json
{
  "type": "websocket.disconnect",
  "code": 1000
}
```

**Common status codes:**

- `1000` = Normal closure  
- `1006` = Abnormal closure

**Handler example:**

```python
def websocket_disconnect(self, event):
    raise StopConsumer()
```

#### 5. `websocket.close` (Server → Client)

Used to explicitly terminate the connection from the server.

```json
{
  "type": "websocket.close",
  "code": 4000,
  "reason": "Invalid session token"
}
```

**Close with reason:**

```python
self.send({
    "type": "websocket.close",
    "code": 4000,
    "reason": "Invalid session token"
})
```

Useful for:

- Kicking users out  
- Invalid auth  
- Session timeout  

### Summary Table

| Event Type            | Triggered By     | Handler / Response                          |
|------------------------|------------------|---------------------------------------------|
| `websocket.connect`    | Client           | Accept using `websocket_accept()`           |
| `websocket.receive`    | Client           | Use `websocket_receive()`                   |
| `websocket.send`       | Server           | Use `self.send(type="websocket.send")`      |
| `websocket.disconnect` | Client/Server    | Use `websocket_disconnect()` for cleanup    |
| `websocket.close`      | Server           | Use `self.send(type="websocket.close")`     |

---

## ASGI Scope Is Created

Every WebSocket connection has a scope — a dictionary that includes:

```python
{
    "type": "websocket",
    "path": "/ws/chat/",
    "headers": [...],
    "query_string": b"room=abc",
    "user": <AuthenticatedUser>,
    "client": ("127.0.0.1", 54321),
    ...
}
```

### Why this matters:

- You can access `self.scope["user"]`, `self.scope["path"]`, `self.scope["query_string"]`, etc.
- It's available throughout the lifetime of the connection.

### Example: ASGI Scope Structure

```python
{
    "type": "websocket",
    "path": "/ws/chat/",
    "headers": [
        [b"host", b"localhost:8000"],
        [b"user-agent", b"Mozilla/5.0"],
        [b"origin", b"http://localhost:3000"],
        [b"cookie", b"sessionid=xyz"]
    ],
    "query_string": b"room=abc",
    "path_remaining": "",
    "raw_path": b"/ws/chat/",
    "scheme": "ws",
    "client": ("127.0.0.1", 54321),
    "server": ("127.0.0.1", 8000),
    "subprotocols": [],
    "user": <AuthenticatedUser>,
    "session": <Session object>,
    "cookies": { "sessionid": "xyz" },
    "root_path": "",
    "asgi": {
        "version": "3.0"
    }
}
```

> The `scope` is available in all lifecycle methods:
> - `connect()`
> - `receive()`
> - `disconnect()`

### Why the ASGI Scope Matters

You can use keys in `self.scope` to personalize, restrict, or analyze WebSocket connections.

| Key            | Description                                                |
|----------------|------------------------------------------------------------|
| `type`         | Type of ASGI connection (e.g., `"websocket"`)              |
| `path`         | Full request path (e.g., `/ws/chat/`)                      |
| `query_string` | Raw bytes query string (e.g., `b"room=abc"`)               |
| `headers`      | List of `[key, value]` byte pairs                          |
| `user`         | Authenticated user (if using `AuthMiddlewareStack`)        |
| `client`       | Client IP and port tuple                                   |
| `cookies`      | Dict of cookie names and values                            |
| `session`      | Django session object (if middleware is enabled)           |

### Accessing Scope in a Consumer

```python
from channels.generic.websocket import AsyncWebsocketConsumer

class MyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        path = self.scope["path"]
        query = self.scope["query_string"].decode()
        client_ip = self.scope["client"][0]

        print(f"User: {user}, Path: {path}, Query: {query}, IP: {client_ip}")

        await self.accept()
```

### Use Case: Query String Parsing

Extract parameters like `room=abc` from the query string:

```python
import urllib.parse

query_string = self.scope["query_string"].decode()
query_params = urllib.parse.parse_qs(query_string)
room = query_params.get("room", ["default"])[0]
```

### Use Case: Access Control

Disconnect unauthenticated users:

```python
if self.scope["user"].is_anonymous:
    await self.close()
```

### Important: Middleware Requirements

The keys `scope["user"]` and `scope["session"]` are populated **only if you use `AuthMiddlewareStack`**.

#### Example:

```python
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path
from .consumers import MyConsumer

application = ProtocolTypeRouter({
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path("ws/chat/", MyConsumer.as_asgi()),
        ])
    )
})
```

If you skip the middleware stack:

- `scope["user"]` will default to `AnonymousUser`
- `scope["session"]` won't be available

---

## Full WebSocket Flow in Django Channels — With Deep Explanations

### 1. Client Initiates a WebSocket Handshake

#### What happens:

The browser creates a WebSocket connection:

```js
const socket = new WebSocket("ws://localhost:8000/ws/chat/");
```

#### What is sent:

This sends a special HTTP GET request with headers like:

```http
GET /ws/chat/ HTTP/1.1
Host: localhost:8000
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: <base64-random>
Sec-WebSocket-Version: 13
Origin: http://localhost:8000
```

#### What it means: 
- This is a request to upgrade the HTTP connection to a WebSocket connection.

### Header-by-Header Breakdown

#### 1. `GET /ws/chat/ HTTP/1.1`

- What it is: The path to the WebSocket endpoint.
- Matched in `routing.py` via `path("ws/chat/", ...)`.
- Why it matters: Determines which consumer will handle the connection.

#### 2. `Host: localhost:8000`

- What it is: Standard HTTP/1.1 header for domain and port.
- Used for: Virtual host routing and same-origin policy.
- Required in all HTTP/1.1 requests.

#### 3. `Upgrade: websocket`

- What it is: Indicates the client wants to switch to the WebSocket protocol.
- Why important: Initiates the protocol upgrade.
- If missing: The server will treat the request as a normal HTTP request.

#### 4. `Connection: Upgrade`

- What it is: Tells the server to interpret the `Upgrade` header.
- Works with `Upgrade: websocket` to trigger a protocol switch.
- Must be present or the upgrade is ignored.

> These two headers must work together:
> - `Connection: Upgrade` means "please process the Upgrade header."
> - `Upgrade: websocket` says "upgrade to the WebSocket protocol."

#### 5. `Sec-WebSocket-Key`

- What it is: A 16-byte random base64-encoded string.
- Purpose: Prevents replay attacks and caching; validates the handshake.
- The server will:
  1. Concatenate this with `"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"`
  2. SHA-1 hash the result
  3. Base64-encode the hash
  4. Return the result in `Sec-WebSocket-Accept`

#### 6. `Sec-WebSocket-Version: 13`

- What it is: Indicates the WebSocket protocol version being used.
- Only version 13 is officially supported.
- Any other version: handshake is rejected.

#### 7. `Origin: http://localhost:8000` (Optional)

- What it is: Specifies the origin of the WebSocket client (browser script).
- Used for: Cross-origin access control and security.
- Server can choose to accept or reject based on this.

### Server → Client: WebSocket Handshake Response Headers

If the server accepts the upgrade, it responds with:

```http
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

#### 1. `101 Switching Protocols`

- What it is: An HTTP status code indicating the protocol switch.
- Purpose: Confirms the upgrade from HTTP to WebSocket.

#### 2. `Upgrade: websocket`

- What it is: Confirms the new protocol is now WebSocket.
- Completes the upgrade handshake initiated by the client.

#### 3. `Connection: Upgrade`

- What it is: Confirms the connection has successfully been upgraded.

#### 4. `Sec-WebSocket-Accept`

- What it is: A hash-based response used to validate the handshake.
- Created by:
  - `hash = SHA1(client_key + magic_guid)`
  - `base64(hash)`
- Purpose: Confirms the server received and recognized the client's key.
- Used to prove the handshake is legitimate and not cached or spoofed.

### Summary Table

| Header                    | Direction | Required       | Purpose                                          |
|---------------------------|-----------|----------------|--------------------------------------------------|
| `GET /ws/chat/ HTTP/1.1`  | Client    | Yes            | Route path to the WebSocket endpoint             |
| `Host`                    | Client    | Yes            | Specifies server host and port                   |
| `Upgrade: websocket`      | Client    | Yes            | Requests protocol upgrade                        |
| `Connection: Upgrade`     | Client    | Yes            | Enables processing of the upgrade request        |
| `Sec-WebSocket-Key`       | Client    | Yes            | Random key for validating handshake              |
| `Sec-WebSocket-Version`   | Client    | Yes            | Must be version 13                               |
| `Origin`                  | Client    | Optional       | Used for cross-origin access control             |
| `101 Switching Protocols` | Server    | Yes            | Acknowledges the upgrade                         |
| `Sec-WebSocket-Accept`    | Server    | Yes            | Proves handshake is valid                        |

### 2. ASGI Application Receives the Request

#### File: `asgi.py`

```python
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
import app.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(app.routing.websocket_urlpatterns)
    ),
})
```

#### What this does:

- `ProtocolTypeRouter`: Inspects the type of incoming connection (`http`, `websocket`, etc.).
- If it's HTTP → handled by Django.
- If it's WebSocket → passed to the next layer:
  - `AuthMiddlewareStack`: Adds `scope["user"]` using session cookies.
  - `URLRouter`: Matches path like `/ws/chat/` to a consumer class.

### 3. Routing the WebSocket Path

Uses Django's `path()` just like `urls.py`.

### 4. ASGI Scope Is Created

Already covered above.

### 5. Consumer is Instantiated

The matching consumer (e.g., `ChatConsumer`) is created per client connection.

#### What happens:

- Django Channels calls `websocket_connect(event)`
- You must call `await self.accept()` to formally complete the handshake.
- If you don't call `accept()`, the connection will be dropped by the server.

### 6. Client Sends a Message

```js
socket.send("Hello, server!");
```

#### Django receives:

```json
{
  "type": "websocket.receive",
  "text": "Hello, server!"
}
```

#### Method triggered:

```python
async def websocket_receive(self, event):
    message = event["text"]
    await self.send(text_data=f"You said: {message}")
```

#### Key actions:

- `websocket_receive()` is called with the client's message.
- `self.send()` sends a message back to the client.
- You can also process the message, query the database, etc.

### 7. Server Sends a Message to Client

#### Python (server) code:

```python
await self.send(text_data="Welcome to the chat")
```

#### Browser receives:

```js
socket.onmessage = (event) => {
    console.log(event.data); // "Welcome to the chat"
};
```

WebSocket is now full-duplex — either side can send messages at any time.

### 8. Disconnection and Cleanup

#### When it happens:

- Client closes tab or socket
- Server disconnects due to timeout, error, or command

#### What gets triggered:

```python
async def websocket_disconnect(self, event):
    print("Disconnected:", event["code"])
```

#### What to do:

- Leave chat groups
- Save data to DB
- Log events
- Clean resources

### 9. Optional: Closing the Connection Manually

#### Server can close the connection like this:

```python
await self.close(code=4001, reason="Unauthorized user")
```

#### Client gets:

```json
{
  "type": "websocket.close",
  "code": 4001,
  "reason": "Unauthorized user"
}
```

#### Browser will call:

```js
socket.onclose = (event) => {
    console.log(event.code);   // 4001
    console.log(event.reason); // Unauthorized user
};
```

### Example: Full Minimal Consumer

```python
from channels.generic.websocket import AsyncWebsocketConsumer

class EchoConsumer(AsyncWebsocketConsumer):
    async def websocket_connect(self, event):
        await self.accept()

    async def websocket_receive(self, event):
        msg = event["text"]
        await self.send(text_data=f"You said: {msg}")

    async def websocket_disconnect(self, event):
        print("Disconnected")
```

### Full Lifecycle Recap

| Step | Event / Action              | Code Involved                            |
| ---- | --------------------------- | ---------------------------------------- |
| 1    | Client sends handshake      | `new WebSocket("ws://...")`              |
| 2    | ASGI layer detects protocol | `ProtocolTypeRouter`                     |
| 3    | Authentication scope added  | `AuthMiddlewareStack`                    |
| 4    | Path matched to consumer    | `URLRouter(websocket_urlpatterns)`       |
| 5    | Consumer instantiated       | `ChatConsumer.as_asgi()`                 |
| 6    | `websocket_connect()` runs  | Must call `await self.accept()`          |
| 7    | Client sends message        | Triggers `websocket_receive()`           |
| 8    | Server sends message        | Via `await self.send(text_data=...)`     |
| 9    | Either side disconnects     | Triggers `websocket_disconnect()`        |
| 10   | Server can close connection | `await self.close(code=..., reason=...)` |

---

## Final Result

- WebSocket endpoint: `ws://localhost:8000/ws/chat/`
- Ready for:
  - Real-time chat
  - Live notifications
  - Collaborative features
  - IoT streaming
 
## 🔁 WebSocket Events (Listeners)

### 1️⃣ Event: `open`
**Triggered when:** Connection successfully established

```javascript
ws.addEventListener('open', (event) => {
    console.log("✅ Connection established");
    console.log("Protocol:", event.target.protocol);
    console.log("Extensions:", event.target.extensions);
});

// Alternative syntax
ws.onopen = (event) => {
    console.log("✅ Connected to server");
    // Send initial message
    ws.send("Hello from client!");
};
```

**Best practices:**
- Initialize application state
- Send authentication tokens
- Start heartbeat/ping mechanisms
- Update UI to show "connected" status

**Event properties:**
- `event.target` - The WebSocket instance
- `event.type` - Always "open"

---

### 2️⃣ Event: `message`
**Triggered when:** Server sends data to client

```javascript
ws.onmessage = (event) => {
    console.log("📩 Received:", event.data);
    
    // Handle different data types
    if (typeof event.data === 'string') {
        const data = JSON.parse(event.data);
        console.log("JSON data:", data);
    } else if (event.data instanceof Blob) {
        console.log("Binary data (Blob):", event.data);
    } else if (event.data instanceof ArrayBuffer) {
        console.log("Binary data (ArrayBuffer):", event.data);
    }
};

// With addEventListener
ws.addEventListener('message', (event) => {
    try {
        const message = JSON.parse(event.data);
        handleMessage(message);
    } catch (error) {
        console.error("Failed to parse message:", error);
    }
});
```

**Event properties:**
- `event.data` - The message data (string, Blob, or ArrayBuffer)
- `event.origin` - Origin of the message
- `event.lastEventId` - Last event ID (for Server-Sent Events compatibility)

**Data types:**
- **Text**: UTF-8 strings (most common)
- **Binary**: Blob or ArrayBuffer for files, images, etc.

---

### 3️⃣ Event: `close`
**Triggered when:** Connection is closed (by client, server, or network)

```javascript
ws.addEventListener('close', (event) => {
    console.log("🔌 Connection closed");
    console.log("Code:", event.code);
    console.log("Reason:", event.reason);
    console.log("Clean close:", event.wasClean);
    
    // Handle different close scenarios
    if (event.code === 1000) {
        console.log("Normal closure");
    } else if (event.code === 1006) {
        console.log("Abnormal closure - attempting reconnect");
        setTimeout(reconnect, 3000);
    }
});

// Alternative syntax
ws.onclose = (event) => {
    updateUI("disconnected");
    if (!event.wasClean) {
        console.warn("Connection lost unexpectedly");
        attemptReconnection();
    }
};
```

**Event properties:**
- `event.code` - Close status code (see codes below)
- `event.reason` - Human-readable close reason
- `event.wasClean` - Boolean indicating if close was clean

**Common close codes:**
- `1000` - Normal closure
- `1001` - Going away (page refresh/navigation)
- `1002` - Protocol error
- `1003` - Unsupported data type
- `1006` - Abnormal closure (no close frame)
- `1011` - Server error
- `4000-4999` - Custom application codes

---

### 4️⃣ Event: `error`
**Triggered when:** Connection or transmission error occurs

```javascript
ws.onerror = (error) => {
    console.error("❌ WebSocket error:", error);
    console.error("Error type:", error.type);
    console.error("Target:", error.target);
    
    // Handle error scenarios
    showErrorMessage("Connection failed. Retrying...");
    scheduleReconnect();
};

// With addEventListener
ws.addEventListener('error', (error) => {
    console.error("WebSocket error details:", {
        type: error.type,
        target: error.target.url,
        readyState: error.target.readyState
    });
});
```

**Event properties:**
- `event.type` - Always "error"
- `event.target` - The WebSocket instance that errored

**Common error scenarios:**
- Connection refused (server down)
- Network timeout
- Invalid URL or protocol
- Certificate/SSL issues
- Server explicitly rejecting connection

---

## ⚙️ WebSocket Methods (Actions)

### 1️⃣ Method: `send()`
**Purpose:** Send data to the server

```javascript
// Send text data
ws.send("Hello server!");

// Send JSON data
const data = { type: "chat", message: "Hello", user: "john" };
ws.send(JSON.stringify(data));

// Send binary data (Blob)
const blob = new Blob(["binary data"], { type: "application/octet-stream" });
ws.send(blob);

// Send binary data (ArrayBuffer)
const buffer = new ArrayBuffer(8);
const view = new Uint8Array(buffer);
view[0] = 65; // ASCII 'A'
ws.send(buffer);

// Safe sending with readyState check
function safeSend(message) {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(message);
    } else {
        console.warn("Cannot send: WebSocket not open");
        queueMessage(message); // Queue for later
    }
}
```

**Important notes:**
- Only works when `readyState === WebSocket.OPEN` (1)
- Throws error if called on closed connection
- Supports text (string) and binary (Blob/ArrayBuffer) data
- No return value - fire and forget

**Data size limits:**
- Browser dependent (typically 64KB - 1MB chunks)
- Large data should be chunked manually

---

### 2️⃣ Method: `close()`
**Purpose:** Gracefully close the WebSocket connection

```javascript
// Normal close
ws.close();

// Close with status code
ws.close(1000); // Normal closure

// Close with code and reason
ws.close(1000, "Chat session ended");

// Close with custom application code
ws.close(4000, "User logout");

// Error-triggered close
ws.close(1011, "Server error occurred");
```

**Parameters:**
- `code` (optional) - Close status code (1000-4999)
- `reason` (optional) - UTF-8 string (max 123 bytes)

**Status code ranges:**
- `1000-1015` - Standard codes
- `3000-3999` - Library/framework codes
- `4000-4999` - Application-specific codes

**Important notes:**
- Calling `close()` multiple times is safe
- Connection may not close immediately
- Triggers `close` event when complete

---

### 3️⃣ Property: `readyState`
**Purpose:** Check current connection status

```javascript
// Check before sending
if (ws.readyState === WebSocket.OPEN) {
    ws.send("Safe to send!");
}

// Handle all states
switch (ws.readyState) {
    case WebSocket.CONNECTING: // 0
        console.log("🔄 Connecting...");
        showSpinner();
        break;
    case WebSocket.OPEN: // 1
        console.log("✅ Connected");
        enableChatInput();
        break;
    case WebSocket.CLOSING: // 2
        console.log("🔄 Closing...");
        disableChatInput();
        break;
    case WebSocket.CLOSED: // 3
        console.log("❌ Closed");
        showReconnectButton();
        break;
}

// Utility function
function isConnected(ws) {
    return ws.readyState === WebSocket.OPEN;
}

// Wait for connection
function waitForConnection(ws, callback) {
    if (ws.readyState === WebSocket.OPEN) {
        callback();
    } else {
        ws.addEventListener('open', callback, { once: true });
    }
}
```

**ReadyState constants:**
- `WebSocket.CONNECTING` (0) - Connection not yet open
- `WebSocket.OPEN` (1) - Connection open and ready
- `WebSocket.CLOSING` (2) - Connection in closing handshake
- `WebSocket.CLOSED` (3) - Connection closed or couldn't open

---

### 4️⃣ Property: `url`
**Purpose:** Get the WebSocket URL

```javascript
console.log("Connected to:", ws.url);
// Output: "ws://localhost:8000/ws/chat/"

// Useful for debugging and logging
function logConnection(ws) {
    console.log(`WebSocket ${ws.readyState === WebSocket.OPEN ? 'connected to' : 'attempting'}: ${ws.url}`);
}
```

---

### 5️⃣ Property: `protocol`
**Purpose:** Get the selected subprotocol

```javascript
// When creating WebSocket with subprotocols
const ws = new WebSocket("ws://localhost:8000/ws/chat/", ["chat", "echo"]);

ws.onopen = () => {
    console.log("Selected protocol:", ws.protocol);
    // Server chose one of: "chat" or "echo"
};
```

---

### 6️⃣ Property: `extensions`
**Purpose:** Get negotiated extensions

```javascript
ws.onopen = () => {
    console.log("Active extensions:", ws.extensions);
    // e.g., "permessage-deflate"
};
```

---

## 📝 Complete Example: Chat Application

```javascript
class ChatWebSocket {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.messageQueue = [];
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        
        this.connect();
    }
    
    connect() {
        console.log(`Connecting to ${this.url}...`);
        this.ws = new WebSocket(this.url);
        
        // Event listeners
        this.ws.onopen = this.handleOpen.bind(this);
        this.ws.onmessage = this.handleMessage.bind(this);
        this.ws.onclose = this.handleClose.bind(this);
        this.ws.onerror = this.handleError.bind(this);
    }
    
    handleOpen(event) {
        console.log("✅ Connected to chat server");
        this.reconnectAttempts = 0;
        
        // Send queued messages
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            this.ws.send(message);
        }
        
        // Update UI
        this.updateStatus("connected");
    }
    
    handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            console.log("📩 Received:", data);
            
            // Handle different message types
            switch (data.type) {
                case 'chat':
                    this.displayChatMessage(data);
                    break;
                case 'user_joined':
                    this.displayUserJoined(data);
                    break;
                case 'error':
                    this.displayError(data.message);
                    break;
            }
        } catch (error) {
            console.error("Failed to parse message:", error);
        }
    }
    
    handleClose(event) {
        console.log(`🔌 Connection closed: ${event.code} - ${event.reason}`);
        this.updateStatus("disconnected");
        
        // Attempt reconnection for abnormal closures
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
        }
    }
    
    handleError(error) {
        console.error("❌ WebSocket error:", error);
        this.updateStatus("error");
    }
    
    send(message) {
        if (this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn("WebSocket not open, queueing message");
            this.messageQueue.push(JSON.stringify(message));
        }
    }
    
    scheduleReconnect() {
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        
        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
        setTimeout(() => this.connect(), delay);
    }
    
    close(code = 1000, reason = "Normal closure") {
        if (this.ws) {
            this.ws.close(code, reason);
        }
    }
    
    updateStatus(status) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = `status ${status}`;
        }
    }
    
    displayChatMessage(data) {
        const messagesDiv = document.getElementById('messages');
        const messageElement = document.createElement('div');
        messageElement.innerHTML = `<strong>${data.user}:</strong> ${data.message}`;
        messagesDiv.appendChild(messageElement);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    
    displayUserJoined(data) {
        const messagesDiv = document.getElementById('messages');
        const messageElement = document.createElement('div');
        messageElement.innerHTML = `<em>${data.user} joined the chat</em>`;
        messageElement.className = 'system-message';
        messagesDiv.appendChild(messageElement);
    }
    
    displayError(message) {
        const errorDiv = document.getElementById('error-messages');
        const errorElement = document.createElement('div');
        errorElement.textContent = message;
        errorElement.className = 'error';
        errorDiv.appendChild(errorElement);
        
        // Auto-remove after 5 seconds
        setTimeout(() => errorElement.remove(), 5000);
    }
}

// Usage
const chat = new ChatWebSocket("ws://localhost:8000/ws/chat/");

// Send message function
function sendMessage() {
    const input = document.getElementById('message-input');
    const message = input.value.trim();
    
    if (message) {
        chat.send({
            type: 'chat',
            message: message,
            user: 'current_user'
        });
        input.value = '';
    }
}

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    chat.close(1001, "Page navigation");
});
```

---

## 📋 Best Practices Summary

### Event Handling
- Always handle all four events (`open`, `message`, `close`, `error`)
- Use `addEventListener` for multiple handlers or `on*` properties for single handlers
- Implement proper error handling and user feedback
- Queue messages when connection is not open

### Connection Management
- Check `readyState` before calling `send()`
- Implement reconnection logic for abnormal closures
- Use exponential backoff for reconnection attempts
- Provide clear UI feedback for connection status

### Data Handling
- Always try/catch when parsing JSON messages
- Handle both text and binary data appropriately
- Validate message structure and content
- Implement message queuing for offline scenarios

### Resource Cleanup
- Call `close()` when done with WebSocket
- Remove event listeners if using `addEventListener`
- Clear any timers or intervals
- Handle page unload scenarios

# Django Channels Layer and Groups Complete Guide

## What is Channel Layer?

**Channel Layer** is Django Channels' messaging system that enables communication between different parts of your application:

- **Between different WebSocket consumers**
- **Between consumers and Django views**
- **Between consumers and background tasks**
- **Between different server instances** (in production)

Think of it as a **message broker** or **pub/sub system** for real-time applications.

---

## Core Concepts

### 1. **Channel**
- A **unique identifier** for a single WebSocket connection
- Each consumer instance gets a unique channel name
- Format: `websocket.send.AbCdEfGh123`

### 2. **Group**
- A **collection of channels** that can receive the same message
- Named collections (e.g., `chat_room_1`, `notifications`)
- Channels can join/leave groups dynamically

### 3. **Channel Layer**
- The **infrastructure** that routes messages between channels and groups
- Stores group memberships and message queues
- Usually backed by **Redis** or **in-memory** for development

---

## Architecture Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                    Channel Layer                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Group A   │  │   Group B   │  │   Group C   │        │
│  │             │  │             │  │             │        │
│  │ Channel 1   │  │ Channel 2   │  │ Channel 1   │        │
│  │ Channel 3   │  │ Channel 4   │  │ Channel 5   │        │
│  │ Channel 5   │  │             │  │             │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
        ↑                   ↑                   ↑
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Client 1   │    │   Client 2   │    │   Client 3   │
│ (WebSocket)  │    │ (WebSocket)  │    │ (WebSocket)  │
└──────────────┘    └──────────────┘    └──────────────┘
```

---

## Channel Layer Configuration

### 1. **Development Setup (In-Memory)**

```python
# settings.py
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}
```

**Pros:**
- No additional dependencies
- Good for testing and development

**Cons:**
- Single server only
- Data lost on restart
- Not suitable for production

### 2. **Production Setup (Redis)**

```python
# settings.py
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
            "capacity": 1500,  # Maximum messages in channel
            "expiry": 60,      # Message expiry time in seconds
        },
    },
}
```

**Installation:**
```bash
pip install channels-redis
```

**Advanced Redis Configuration:**
```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [
                {
                    "address": "redis://username:password@127.0.0.1:6379/0",
                    "db": 0,
                }
            ],
            "prefix": "django_channels:",
            "capacity": 1500,
            "expiry": 60,
            "group_expiry": 86400,  # 24 hours
            "symmetric_encryption_keys": ["secret-key-1", "secret-key-2"],
        },
    },
}
```

### 3. **Testing Channel Layer**

```python
# Test in Django shell
python manage.py shell

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

channel_layer = get_channel_layer()

# Test basic functionality
async_to_sync(channel_layer.send)("test-channel", {"type": "test.message", "text": "Hello!"})
message = async_to_sync(channel_layer.receive)(["test-channel"])
print(message)  # Should print the message
```

---

## Groups in Detail

### What are Groups?

Groups are **named collections of channels** that allow you to:
- **Broadcast messages** to multiple clients simultaneously
- **Organize clients** by functionality (chat rooms, notification types)
- **Manage subscriptions** dynamically

### Group Operations

#### 1. **Adding Channel to Group**

```python
# In a consumer
await self.channel_layer.group_add(
    "chat_room_1",      # Group name
    self.channel_name   # Channel to add
)
```

#### 2. **Removing Channel from Group**

```python
await self.channel_layer.group_discard(
    "chat_room_1",      # Group name
    self.channel_name   # Channel to remove
)
```

#### 3. **Sending Message to Group**

```python
await self.channel_layer.group_send(
    "chat_room_1",      # Group name
    {
        "type": "chat_message",    # Consumer method to call
        "message": "Hello everyone!",
        "sender": "user123"
    }
)
```

---

## Complete Example: Chat Room

### 1. **Consumer Implementation**

```python
# consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Extract room name from URL
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Notify others that user joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'username': self.get_username(),
                'channel_name': self.channel_name
            }
        )
    
    async def disconnect(self, close_code):
        # Notify others that user left
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'username': self.get_username(),
                'channel_name': self.channel_name
            }
        )
        
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type', 'chat_message')
        
        if message_type == 'chat_message':
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': data['message'],
                    'username': self.get_username(),
                    'timestamp': self.get_timestamp()
                }
            )
        elif message_type == 'typing':
            # Send typing indicator
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'username': self.get_username(),
                    'is_typing': data.get('is_typing', False)
                }
            )
    
    # Handler methods (called by channel layer)
    async def chat_message(self, event):
        """Send chat message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'username': event['username'],
            'timestamp': event['timestamp']
        }))
    
    async def user_joined(self, event):
        """Handle user joined event"""
        if event['channel_name'] != self.channel_name:  # Don't notify self
            await self.send(text_data=json.dumps({
                'type': 'user_joined',
                'username': event['username'],
                'message': f"{event['username']} joined the room"
            }))
    
    async def user_left(self, event):
        """Handle user left event"""
        if event['channel_name'] != self.channel_name:  # Don't notify self
            await self.send(text_data=json.dumps({
                'type': 'user_left',
                'username': event['username'],
                'message': f"{event['username']} left the room"
            }))
    
    async def typing_indicator(self, event):
        """Handle typing indicator"""
        if event['username'] != self.get_username():  # Don't send to self
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'username': event['username'],
                'is_typing': event['is_typing']
            }))
    
    def get_username(self):
        """Get username from scope"""
        user = self.scope.get('user')
        if user and user.is_authenticated:
            return user.username
        return 'Anonymous'
    
    def get_timestamp(self):
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
```

### 2. **URL Routing**

```python
# routing.py
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/chat/<str:room_name>/', consumers.ChatConsumer.as_asgi()),
]
```

### 3. **Client-Side JavaScript**

```javascript
// Client-side implementation
class ChatRoom {
    constructor(roomName, username) {
        this.roomName = roomName;
        this.username = username;
        this.socket = null;
        this.connect();
    }
    
    connect() {
        const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
        const wsPath = `${wsScheme}://${window.location.host}/ws/chat/${this.roomName}/`;
        
        this.socket = new WebSocket(wsPath);
        
        this.socket.onopen = (e) => {
            console.log("Connected to chat room");
            this.updateStatus("Connected");
        };
        
        this.socket.onmessage = (e) => {
            const data = JSON.parse(e.data);
            this.handleMessage(data);
        };
        
        this.socket.onclose = (e) => {
            console.log("Disconnected from chat room");
            this.updateStatus("Disconnected");
            // Attempt to reconnect
            setTimeout(() => this.connect(), 3000);
        };
        
        this.socket.onerror = (e) => {
            console.error("WebSocket error:", e);
        };
    }
    
    handleMessage(data) {
        switch (data.type) {
            case 'chat_message':
                this.displayMessage(data);
                break;
            case 'user_joined':
            case 'user_left':
                this.displaySystemMessage(data.message);
                break;
            case 'typing':
                this.handleTyping(data);
                break;
        }
    }
    
    sendMessage(message) {
        if (this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                'type': 'chat_message',
                'message': message
            }));
        }
    }
    
    sendTyping(isTyping) {
        if (this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                'type': 'typing',
                'is_typing': isTyping
            }));
        }
    }
    
    displayMessage(data) {
        const messagesDiv = document.getElementById('chat-messages');
        const messageElement = document.createElement('div');
        messageElement.className = 'message';
        messageElement.innerHTML = `
            <span class="username">${data.username}:</span>
            <span class="text">${data.message}</span>
            <span class="timestamp">${new Date(data.timestamp).toLocaleTimeString()}</span>
        `;
        messagesDiv.appendChild(messageElement);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    
    displaySystemMessage(message) {
        const messagesDiv = document.getElementById('chat-messages');
        const messageElement = document.createElement('div');
        messageElement.className = 'system-message';
        messageElement.textContent = message;
        messagesDiv.appendChild(messageElement);
    }
    
    handleTyping(data) {
        const typingDiv = document.getElementById('typing-indicators');
        const indicatorId = `typing-${data.username}`;
        
        if (data.is_typing) {
            if (!document.getElementById(indicatorId)) {
                const indicator = document.createElement('div');
                indicator.id = indicatorId;
                indicator.textContent = `${data.username} is typing...`;
                typingDiv.appendChild(indicator);
            }
        } else {
            const indicator = document.getElementById(indicatorId);
            if (indicator) {
                indicator.remove();
            }
        }
    }
    
    updateStatus(status) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = status.toLowerCase();
        }
    }
}

// Usage
const chat = new ChatRoom('general', 'john_doe');

// Send message
document.getElementById('send-button').onclick = () => {
    const input = document.getElementById('message-input');
    const message = input.value.trim();
    if (message) {
        chat.sendMessage(message);
        input.value = '';
    }
};

// Typing indicators
let typingTimer;
document.getElementById('message-input').onkeypress = (e) => {
    chat.sendTyping(true);
    clearTimeout(typingTimer);
    typingTimer = setTimeout(() => {
        chat.sendTyping(false);
    }, 1000);
};
```

---

## Advanced Group Patterns

### 1. **Multiple Group Memberships**

```python
class MultiGroupConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        
        # Join multiple groups
        groups = [
            "global_notifications",
            f"user_{self.scope['user'].id}",
            "moderators" if self.scope['user'].is_staff else "users"
        ]
        
        for group in groups:
            await self.channel_layer.group_add(group, self.channel_name)
```

### 2. **Dynamic Group Creation**

```python
async def create_temporary_group(self):
    """Create a temporary group for a specific event"""
    group_name = f"event_{uuid.uuid4().hex[:8]}"
    
    # Add interested channels to the group
    await self.channel_layer.group_add(group_name, self.channel_name)
    
    # Schedule group cleanup
    asyncio.create_task(self.cleanup_group_later(group_name, 3600))  # 1 hour
    
    return group_name

async def cleanup_group_later(self, group_name, delay):
    """Remove all channels from group after delay"""
    await asyncio.sleep(delay)
    # Group cleanup happens automatically when last channel leaves
```

### 3. **Hierarchical Groups**

```python
class HierarchicalConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        
        # Join hierarchical groups
        groups = [
            "all_users",                           # Global
            f"department_{user.department.id}",    # Department level
            f"team_{user.team.id}",               # Team level
            f"user_{user.id}"                     # Individual level
        ]
        
        for group in groups:
            await self.channel_layer.group_add(group, self.channel_name)
    
    async def send_announcement(self, scope, message):
        """Send message to appropriate scope"""
        scope_groups = {
            'global': 'all_users',
            'department': f"department_{self.get_user_department()}",
            'team': f"team_{self.get_user_team()}",
            'personal': f"user_{self.scope['user'].id}"
        }
        
        group_name = scope_groups.get(scope)
        if group_name:
            await self.channel_layer.group_send(
                group_name,
                {
                    'type': 'announcement',
                    'message': message,
                    'scope': scope
                }
            )
```

---

## External Triggers (Django Views/Tasks)

### 1. **From Django Views**

```python
# views.py
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.http import JsonResponse

def send_notification(request):
    """Send notification via WebSocket from a regular Django view"""
    channel_layer = get_channel_layer()
    
    # Send to specific group
    async_to_sync(channel_layer.group_send)(
        "notifications",
        {
            "type": "notification_message",
            "message": "New system update available",
            "level": "info",
            "timestamp": timezone.now().isoformat()
        }
    )
    
    return JsonResponse({"status": "notification sent"})

def broadcast_maintenance(request):
    """Broadcast maintenance message to all connected users"""
    channel_layer = get_channel_layer()
    
    async_to_sync(channel_layer.group_send)(
        "all_users",
        {
            "type": "maintenance_alert",
            "message": "System maintenance in 10 minutes",
            "countdown": 600,  # 10 minutes in seconds
            "action_required": True
        }
    )
    
    return JsonResponse({"status": "maintenance alert sent"})
```

### 2. **From Celery Tasks**

```python
# tasks.py
from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@shared_task
def send_scheduled_notification():
    """Send scheduled notification via WebSocket"""
    channel_layer = get_channel_layer()
    
    async_to_sync(channel_layer.group_send)(
        "notifications",
        {
            "type": "scheduled_notification",
            "message": "Daily backup completed successfully",
            "category": "system",
            "timestamp": timezone.now().isoformat()
        }
    )

@shared_task
def process_user_activity(user_id, activity_type):
    """Process user activity and notify relevant groups"""
    channel_layer = get_channel_layer()
    
    # Notify user's team
    async_to_sync(channel_layer.group_send)(
        f"team_updates_{get_user_team(user_id)}",
        {
            "type": "activity_update",
            "user_id": user_id,
            "activity": activity_type,
            "timestamp": timezone.now().isoformat()
        }
    )
```

### 3. **From Django Signals**

```python
# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@receiver(post_save, sender=Message)
def notify_new_message(sender, instance, created, **kwargs):
    """Notify users when new message is created"""
    if created:
        channel_layer = get_channel_layer()
        
        # Notify all users in the conversation
        async_to_sync(channel_layer.group_send)(
            f"conversation_{instance.conversation.id}",
            {
                "type": "new_message",
                "message_id": instance.id,
                "sender": instance.sender.username,
                "content": instance.content,
                "timestamp": instance.created_at.isoformat()
            }
        )

@receiver(post_save, sender=User)
def notify_user_status_change(sender, instance, **kwargs):
    """Notify when user comes online/offline"""
    if hasattr(instance, '_status_changed'):
        channel_layer = get_channel_layer()
        
        async_to_sync(channel_layer.group_send)(
            "user_status_updates",
            {
                "type": "user_status_change",
                "user_id": instance.id,
                "username": instance.username,
                "is_online": instance.is_online,
                "last_seen": instance.last_seen.isoformat()
            }
        )
```

---

## Performance Considerations

### 1. **Group Size Limits**

```python
# Large groups can impact performance
# Consider pagination for very large groups

class OptimizedConsumer(AsyncWebsocketConsumer):
    MAX_GROUP_SIZE = 1000
    
    async def join_large_group(self, base_group_name):
        """Distribute users across multiple sub-groups"""
        group_count = await self.get_group_count(base_group_name)
        
        if group_count >= self.MAX_GROUP_SIZE:
            # Create new sub-group
            sub_group_index = group_count // self.MAX_GROUP_SIZE
            group_name = f"{base_group_name}_{sub_group_index}"
        else:
            group_name = base_group_name
        
        await self.channel_layer.group_add(group_name, self.channel_name)
        return group_name
```

### 2. **Message Size Optimization**

```python
async def send_optimized_message(self, group_name, data):
    """Send optimized message with compression"""
    import json
    import gzip
    
    # Compress large messages
    message_json = json.dumps(data)
    if len(message_json) > 1024:  # 1KB threshold
        compressed = gzip.compress(message_json.encode())
        message = {
            "type": "compressed_message",
            "compressed": True,
            "data": compressed.hex()
        }
    else:
        message = {
            "type": "regular_message",
            "compressed": False,
            "data": data
        }
    
    await self.channel_layer.group_send(group_name, message)
```

### 3. **Connection Cleanup**

```python
class CleanupConsumer(AsyncWebsocketConsumer):
    async def disconnect(self, close_code):
        """Proper cleanup on disconnect"""
        # Remove from all groups
        for group_name in getattr(self, 'joined_groups', []):
            await self.channel_layer.group_discard(group_name, self.channel_name)
        
        # Clear any pending tasks
        for task in getattr(self, 'background_tasks', []):
            task.cancel()
        
        # Log disconnect for monitoring
        logger.info(f"Channel {self.channel_name} disconnected with code {close_code}")
```

---

## Monitoring and Debugging

### 1. **Channel Layer Health Check**

```python
# management/commands/check_channels.py
from django.core.management.base import BaseCommand
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

class Command(BaseCommand):
    def handle(self, *args, **options):
        channel_layer = get_channel_layer()
        
        # Test basic functionality
        test_channel = "test_channel"
        test_message = {"type": "test.message", "text": "Hello"}
        
        try:
            async_to_sync(channel_layer.send)(test_channel, test_message)
            received = async_to_sync(channel_layer.receive)([test_channel])
            
            if received == test_message:
                self.stdout.write(self.style.SUCCESS("Channel layer is working"))
            else:
                self.stdout.write(self.style.ERROR("Channel layer test failed"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Channel layer error: {e}"))
```

### 2. **Group Statistics**

```python
class StatsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        
        # Send current stats
        stats = await self.get_channel_stats()
        await self.send(text_data=json.dumps({
            "type": "stats",
            "data": stats
        }))
    
    async def get_channel_stats(self):
        """Get channel layer statistics"""
        # This would require custom implementation
        # or integration with Redis monitoring
        return {
            "total_channels": await self.count_active_channels(),
            "total_groups": await self.count_active_groups(),
            "messages_per_second": await self.get_message_rate()
        }
```

---

## Security Considerations

### 1. **Group Access Control**

```python
class SecureConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
    
    async def join_group(self, group_name):
        """Join group with permission check"""
        if await self.has_group_permission(group_name):
            await self.channel_layer.group_add(group_name, self.channel_name)
            return True
        else:
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": f"Access denied to group: {group_name}"
            }))
            return False
    
    async def has_group_permission(self, group_name):
        """Check if user can join group"""
        user = self.scope.get('user')
        
        # Example permission logic
        if group_name.startswith('admin_') and not user.is_staff:
            return False
        if group_name.startswith('premium_') and not user.has_premium:
            return False
        
        return True
```

### 2. **Rate Limiting for Groups**

```python
from django.core.cache import cache

class RateLimitedConsumer(AsyncWebsocketConsumer):
    async def receive(self, text_data):
        if not await self.check_rate_limit():
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "Rate limit exceeded"
            }))
            return
        
        # Process message normally
        await self.process_message(text_data)
    
    async def check_rate_limit(self):
        """Check rate limit for this channel"""
        key = f"rate_limit_{self.channel_name}"
        current = cache.get(key, 0)
        
        if current >= 10:  # 10 messages per minute
            return False
        
        cache.set(key, current + 1, 60)  # 60 seconds
        return True
```



