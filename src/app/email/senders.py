import smtplib
from email.utils import formataddr

from pathlib import Path
from string import Template

# Import the email modules we'll need
from email.message import EmailMessage
from typing import Protocol

class EmailSender(Protocol):
    def send_text(
         self,
        *,
        subject: str,
        to: str,
        content: str,
    ) -> None:
        ...
    
    def send_template_html(
         self,
        *,
        subject: str,
        to: str,
        text_content: str,
        html_path: Path,
        template_values: dict[str, str],
    ) -> None:
        ...

class SMTPEmailSender:
    def __init__(
            self,
            *,
            username: str | None,
            password: str | None,
            sender: str | None = None,
            host: str = "smtp.gmail.com",
            port: int = 465,
            from_name = "Kyrg Studio",
        ):

        if username is None:
            raise ValueError("Username is required")
        if password is None:
            raise ValueError("Password is required")
        
        self.username = username
        self.sender = sender if sender is not None else username
        self.password = password
        self.host = host
        self.port = port
        self.from_name = from_name
    

    def send_text(
        self,
        *,
        subject: str,
        to: str,
        content: str,
        ) -> None:
        
        message = self._new_message(
            subject=subject,
            to=to,
            text_content=content,
        )

        self._send_message(message)

    
    def send_template_html(
         self,
        *,
        subject: str,
        to: str,
        text_content: str,
        html_path: Path,
        template_values: dict[str, str],
        ) -> None:
        
        message = self._new_message(
            subject=subject,
            to=to,
            text_content=text_content,
        )
        
        html_template = Template(html_path.read_text(encoding="utf-8"))
        html_content = html_template.safe_substitute(template_values)
        
        message.add_alternative(html_content, subtype="html")

        self._send_message(message)
        
    def _new_message(
        self,
        *,
        subject: str,
        to: str,
        text_content: str,
    ) -> EmailMessage:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = formataddr((self.from_name, self.sender))
        message["To"] = to
        message.set_content(text_content)

        return message
   
    def _send_message(self, message: EmailMessage) -> None:
        with smtplib.SMTP_SSL(self.host, self.port) as smtp:
            smtp.login(self.username, self.password)
            smtp.send_message(message)
            


if __name__ == "__main__":
    from app.settings import load_settings
    
    settings = load_settings()
    
    sender = SMTPEmailSender(
        username=settings.email_username,
        password=settings.email_password,
        host=settings.email_host,
        port=settings.email_port,
    )
    
    sender.send_text(
        subject="Email Teste Kyrgstudio",
        to="ygor.limarsx@gmail.com",
        content="Este é um email teste para o site kygstudio"
    )


