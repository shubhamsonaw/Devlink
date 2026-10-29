"""
ASGI config for Connect project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

# import os
# from channels.routing import ProtocolTypeRouter, URLRouter
# from django.core.asgi import get_asgi_application
# from channels.auth import AuthMiddlewareStack
# import opportunities.routing

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Connect.settings')

# application = get_asgi_application({
#     "http": get_asgi_application(),
#     "websocket": AuthMiddlewareStack(
#         URLRouter(
#             opportunities.routing.websocket_urlpatterns
#         )
#     ),
# })
# ASGI_APPLICATION = "Connect.asgi.application"



import os

from django.core.asgi import get_asgi_application

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

import opportunities.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Connect.settings')

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({

    "http": django_asgi_app,

    "websocket": AuthMiddlewareStack(
        URLRouter(
            opportunities.routing.websocket_urlpatterns
        )
    ),
})