"""Feishu/Lark channel adapter using WebSocket."""

import asyncio
import json
import hmac
import hashlib
import base64
from datetime import datetime
from typing import AsyncIterator, Optional

import aiohttp
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.backends import default_backend

from .base import ChannelAdapter, ChannelError, AuthenticationError, ConnectionError, parse_content
from .types import ChannelMessage, ChannelUser, ChannelContent, ChannelType, ContentType


class FeishuAdapter(ChannelAdapter):
    """Feishu/Lark WebSocket adapter.

    Supports both Feishu (CN) and Lark (Intl) regions via WebSocket.
    """

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        region: str = "cn",
        verify_token: str = "",
        encrypt_key: str = "",
    ):
        """Initialize the Feishu adapter.

        Args:
            app_id: Feishu/Lark app ID.
            app_secret: Feishu/Lark app secret.
            region: "cn" for Feishu, "intl" for Lark.
            verify_token: Optional verification token for event callbacks.
            encrypt_key: Optional AES encryption key for event encryption.
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.region = region
        self.verify_token = verify_token
        self.encrypt_key = encrypt_key

        self._running = False
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._tenant_access_token = ""
        self._token_expires_at = 0

        # API base URLs
        if region == "intl":
            self._api_base = "https://open.larksuite.com"
            self._ws_base = "wss://open.larksuite.com"
        else:
            self._api_base = "https://open.feishu.cn"
            self._ws_base = "wss://open.feishu.cn"

    @property
    def channel_type(self) -> str:
        """Get the channel type identifier."""
        return "feishu" if self.region == "cn" else "lark"

    @property
    def is_running(self) -> bool:
        """Check if the channel is currently running."""
        return self._running

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _refresh_tenant_access_token(self) -> str:
        """Refresh the tenant access token.

        Returns:
            The tenant access token.
        """
        now = asyncio.get_event_loop().time()
        if self._tenant_access_token and now < self._token_expires_at - 60:
            return self._tenant_access_token

        session = await self._get_session()
        url = f"{self._api_base}/open-apis/auth/v3/tenant_access_token/internal"

        response = await session.post(
            url,
            json={
                "app_id": self.app_id,
                "app_secret": self.app_secret,
            },
        )
        data = await response.json()

        if data.get("code") != 0:
            raise AuthenticationError(f"Failed to get tenant access token: {data.get('msg')}")

        self._tenant_access_token = data["tenant_access_token"]
        self._token_expires_at = now + data.get("expire", 7200) - 60  # 1 minute buffer

        return self._tenant_access_token

    async def _decrypt_event(self, encrypted_data: str) -> dict:
        """Decrypt an encrypted Feishu event.

        Args:
            encrypted_data: Base64-encoded encrypted data.

        Returns:
            Decrypted event data as a dictionary.
        """
        if not self.encrypt_key:
            raise ValueError("Encrypt key not set for event decryption")

        # Decode base64
        encrypted_bytes = base64.b64decode(encrypted_data)

        # Extract IV and ciphertext
        iv = encrypted_bytes[:16]
        ciphertext = encrypted_bytes[16:]

        # Create cipher
        key = base64.b64decode(self.encrypt_key)
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()

        # Decrypt and unpad
        decrypted_padded = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = PKCS7(16).unpadder()
        decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()

        # Parse JSON
        return json.loads(decrypted.decode("utf-8"))

    def _verify_event(self, timestamp: str, nonce: str, signature: str) -> bool:
        """Verify an event signature.

        Args:
            timestamp: Event timestamp.
            nonce: Event nonce.
            signature: Event signature.

        Returns:
            True if signature is valid.
        """
        if not self.verify_token:
            return True

        # Calculate expected signature
        message = f"{timestamp}{nonce}{self.verify_token}"
        expected = hmac.new(
            self.verify_token.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    async def _parse_message(self, event: dict) -> Optional[ChannelMessage]:
        """Parse a Feishu event into a ChannelMessage.

        Args:
            event: The Feishu event data.

        Returns:
            A ChannelMessage or None if the event is not a message.
        """
        header = event.get("header", {})
        event_type = header.get("event_type", "")

        # Only process message events
        if event_type != "im.message.receive_v1":
            return None

        event_data = event.get("event", {})
        message_data = event_data.get("message", {})
        sender = event_data.get("sender", {})

        # Extract message content
        content_json = message_data.get("content", "")
        content_data = json.loads(content_json) if isinstance(content_json, str) else content_json

        # Parse different content types
        contents: list[ChannelContent] = []
        msg_type = message_data.get("msg_type", "")

        if msg_type == "text":
            text = content_data.get("text", "")
            contents.append(ChannelContent(type=ContentType.TEXT, text=text))
        elif msg_type == "post":
            post_content = content_data.get("post", {})
            for zone in post_content.get("zh_cn", []) or post_content.get("en_us", []):
                for item in zone.get("text", []):
                    contents.append(ChannelContent(type=ContentType.TEXT, text=item.get("text", "")))
        elif msg_type == "interactive":
            card_content = content_data.get("elements", [])
            # Parse interactive card content
            for element in card_content:
                text = element.get("text", {})
                if isinstance(text, dict):
                    contents.append(ChannelContent(type=ContentType.TEXT, text=text.get("content", "")))
        else:
            # Unknown message type, try to get text representation
            contents.append(ChannelContent(type=ContentType.TEXT, text=str(content_data)))

        # Create user
        user_id = sender.get("sender_id", {}).get("open_id", "")
        sender_type = sender.get("sender_type", "")
        user = ChannelUser(
            id=user_id,
            name=user_id,
            is_bot=sender_type == "app",
        )

        return ChannelMessage(
            id=message_data.get("message_id", ""),
            user=user,
            content=contents,
            channel_type=ChannelType.FEISHU if self.region == "cn" else ChannelType.LARK,
            timestamp=datetime.now(),
            metadata={
                "chat_type": message_data.get("chat_type", ""),
                "chat_id": message_data.get("chat_id", ""),
                "msg_type": msg_type,
                "raw_event": event,
            },
        )

    async def start(self) -> AsyncIterator[ChannelMessage]:
        """Start the Feishu WebSocket and yield incoming messages."""
        if self._running:
            raise ChannelError("Feishu adapter is already running")

        self._running = True
        session = await self._get_session()

        # Get tenant access token
        await self._refresh_tenant_access_token()

        # Build WebSocket URL
        ws_url = f"{self._ws_base}/open-apis/event-connection/v2/client/open?app_id={self.app_id}"

        try:
            async with session.ws_connect(
                ws_url,
                headers={"Authorization": f"Bearer {self._tenant_access_token}"},
            ) as ws:
                self._ws = ws

                while self._running:
                    msg = await ws.receive()

                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        payload = data.get("payload", {})

                        # Parse message events
                        events = payload.get("events", [])
                        for event in events:
                            message = await self._parse_message(event)
                            if message:
                                yield message

                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        raise ConnectionError("WebSocket connection closed")
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        raise ConnectionError(f"WebSocket error: {ws.exception()}")

        except Exception as e:
            self._running = False
            raise ChannelError(f"Feishu WebSocket error: {e}") from e

    async def send(
        self,
        user: ChannelUser,
        content: str | ChannelContent | list[ChannelContent],
        reply_to: Optional[str] = None,
    ) -> bool:
        """Send a message to a Feishu user.

        Args:
            user: The user to send the message to.
            content: The message content.
            reply_to: Optional message ID to reply to.

        Returns:
            True if the message was sent successfully.
        """
        session = await self._get_session()
        token = await self._refresh_tenant_access_token()

        # Get chat_id from metadata or user message
        chat_id = user.metadata.get("chat_id", "") if user.metadata else ""
        if not chat_id:
            chat_id = user.id

        # Parse content
        contents = parse_content(content)

        # Determine message type
        if len(contents) == 1 and contents[0].type == ContentType.TEXT:
            msg_type = "text"
            msg_content = json.dumps({"text": contents[0].text})
        else:
            # For mixed content, use post type
            msg_type = "post"
            post_content = {
                "zh_cn": [[{"tag": "text", "text": c.text} for c in contents if c.type == ContentType.TEXT]]
            }
            msg_content = json.dumps({"post": post_content})

        # Build request URL
        url = f"{self._api_base}/open-apis/im/v1/messages?receive_id_type={self._get_receive_id_type()}"

        # Build request body
        body: dict = {
            "receive_id": chat_id,
            "msg_type": msg_type,
            "content": msg_content,
        }

        if reply_to:
            body["reply_in_thread"] = reply_to

        # Send message
        response = await session.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json=body,
        )
        data = await response.json()

        return data.get("code") == 0

    def _get_receive_id_type(self) -> str:
        """Get the receive ID type based on chat_id format."""
        # Feishu uses different ID types for different contexts
        return "open_id"

    async def send_typing(self, user: ChannelUser) -> bool:
        """Send a typing indicator to a Feishu user.

        Note: Feishu doesn't have a native typing indicator API.
        This is a no-op but kept for API compatibility.

        Returns:
            True (compatibility only).
        """
        # Feishu doesn't support typing indicators
        return True

    async def stop(self) -> None:
        """Stop the Feishu WebSocket connection."""
        self._running = False
        if self._ws and not self._ws.closed:
            await self._ws.close()
        if self._session and not self._session.closed:
            await self._session.close()
