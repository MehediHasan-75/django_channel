from django.shortcuts import render, HttpResponse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
# Create your views here.

def index(request):
    # print("channle name ...", get_channel_layer)
    return render(request, 'app/index.html')


def msgfromounside(request):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "broadcast_group",
        {
            "type": "broadcast_message",  # This should match the method name
            "message": "message from outside"
        }
    )
    return HttpResponse("Message sent from view to consumer")