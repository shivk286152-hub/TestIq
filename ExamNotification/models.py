from django.db import models

# Create your models here.
class ExamNotification(models.Model):
    title = models.CharField(max_length=255)
    short_description = models.TextField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class NotificationHighlight(models.Model):
    notification = models.ForeignKey(
        ExamNotification,
        on_delete=models.CASCADE,
        related_name="highlights"
    )
    text = models.CharField(max_length=255)

    def __str__(self):
        return self.text
class NotificationTable(models.Model):
    notification = models.ForeignKey(
        ExamNotification,
        on_delete=models.CASCADE,
        related_name="tables"
    )
    title = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.title or "Table"
class NotificationTableRow(models.Model):
    table = models.ForeignKey(
        NotificationTable,
        on_delete=models.CASCADE,
        related_name="rows"
    )
class NotificationTableCell(models.Model):
    row = models.ForeignKey(
        NotificationTableRow,
        on_delete=models.CASCADE,
        related_name="cells"
    )
    value = models.CharField(max_length=255)



class NotificationBlock(models.Model):
    TEXT = "text"
    HIGHLIGHT = "highlight"
    TABLE = "table"

    BLOCK_TYPES = [
        (TEXT, "Text"),
        (HIGHLIGHT, "Highlight"),
        (TABLE, "Table"),
    ]

    notification = models.ForeignKey(
        ExamNotification,
        on_delete=models.CASCADE,
        related_name="blocks"
    )
    block_type = models.CharField(max_length=20, choices=BLOCK_TYPES)
    order = models.PositiveIntegerField()
    text = models.TextField(blank=True)

    def __str__(self):
        return f"{self.block_type} block"
