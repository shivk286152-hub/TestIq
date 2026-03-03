from django.shortcuts import render, get_object_or_404
from django.shortcuts import render
from .models import ExamNotification

def notification_list(request):
    notifications = ExamNotification.objects.order_by('-created_at')
    return render(request, 'ExamNotification/list.html', {
        'notifications': notifications
    })


def notification_detail(request, pk):
    notification = get_object_or_404(ExamNotification, pk=pk)
    blocks = notification.blocks.order_by("order")

    return render(request, "ExamNotification/detail.html", {
        "notification": notification,
        "blocks": blocks,
    })
