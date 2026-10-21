from django.core.management.base import BaseCommand

from core.models import User
from core.services.payment_queue import build_payment_queue


class Command(BaseCommand):
    help = "Muestra la cola de pagos pendientes del usuario indicado."

    def add_arguments(self, parser):
        parser.add_argument("email", help="Email del usuario")

    def handle(self, *args, **options):
        user = User.objects.get(email=options["email"])
        queue = build_payment_queue(user)
        if queue.is_empty():
            self.stdout.write("No hay pagos pendientes.")
            return
        for item in queue:
            self.stdout.write(
                f"[Nivel {item.priority}] {item.due_date} "
                f"{item.description} — ${item.amount_pending:,.2f}"
            )
