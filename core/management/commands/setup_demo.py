"""Comando de gestión `setup_demo`: carga datos de demostración para probar FinTrack."""

from calendar import monthrange
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction as db_transaction
from django.utils import timezone

from core.models import (
    Account,
    AccountCreditCardDetails,
    Budget,
    Category,
    Contact,
    ContactGroup,
    Debt,
    Goal,
    SharedExpense,
    Tag,
    Transaction,
    User,
)
from core.services.contacts import add_contact
from core.services.shared_expenses import (
    ParticipantSpec,
    build_participant_specs,
    create_shared_expense,
    register_shared_expense_payment,
)


class Command(BaseCommand):
    """Crea (si no existen) un usuario demo, cuentas, categorías, una etiqueta,
    un presupuesto y transacciones de ejemplo.

    Es idempotente: usa `get_or_create` y hash de contenido para poder
    ejecutarse varias veces sin duplicar datos.
    """

    help = "Carga datos de demostración con usuario demo@fintrack.local / demo1234"

    @db_transaction.atomic
    def handle(self, *args, **options):
        """Ejecuta la carga de datos demo descrita en la docstring de la clase."""
        user, created = User.objects.get_or_create(
            email="demo@fintrack.local",
            defaults={
                "username": "demo",
                "first_name": "Usuario",
                "last_name": "Demo",
            },
        )
        if created:
            user.set_password("demo1234")
            user.save()
            self.stdout.write("Usuario demo creado (demo@fintrack.local / demo1234)")
        else:
            self.stdout.write("Usuario demo ya existe")

        checking, _ = Account.objects.get_or_create(
            user=user,
            name="Cuenta Principal",
            defaults={
                "account_type": "checking",
                "currency": "COP",
                "initial_balance": Decimal("5000.00"),
            },
        )
        savings, _ = Account.objects.get_or_create(
            user=user,
            name="Ahorros",
            defaults={
                "account_type": "savings",
                "currency": "COP",
                "initial_balance": Decimal("10000.00"),
            },
        )

        salary_cat, _ = Category.objects.get_or_create(
            user=user,
            name="Salario",
            category_type="income",
            defaults={"color": "#22c55e"},
        )
        food_cat, _ = Category.objects.get_or_create(
            user=user,
            name="Comida",
            category_type="expense",
            defaults={"color": "#ef4444"},
        )
        transport_cat, _ = Category.objects.get_or_create(
            user=user,
            name="Transporte",
            category_type="expense",
            defaults={"color": "#f59e0b"},
        )

        credit_card, _ = Account.objects.get_or_create(
            user=user,
            name="Tarjeta Visa",
            defaults={
                "account_type": "credit",
                "currency": "COP",
                "initial_balance": Decimal("1500.00"),
            },
        )
        AccountCreditCardDetails.objects.get_or_create(
            account=credit_card,
            defaults={
                "credit_limit": Decimal("8000.00"),
                "statement_day": 5,
                "payment_due_day": 20,
            },
        )

        Tag.objects.get_or_create(user=user, name="recurrente", defaults={"color": "#6366f1"})

        Budget.objects.get_or_create(
            user=user,
            category=food_cat,
            period_start="2026-01-01",
            period_end="2026-01-31",
            defaults={"amount": Decimal("2000.00"), "notes": "Presupuesto mensual de comida"},
        )

        sample_transactions = [
            ("2026-01-01", "income", salary_cat, checking, Decimal("15000.00"), "Salario enero"),
            ("2026-01-05", "expense", food_cat, checking, Decimal("850.00"), "Supermercado"),
            ("2026-01-10", "expense", transport_cat, checking, Decimal("350.00"), "Gasolina"),
            ("2026-01-15", "expense", food_cat, checking, Decimal("120.00"), "Restaurante"),
            ("2026-02-01", "income", salary_cat, checking, Decimal("15000.00"), "Salario febrero"),
            ("2026-02-08", "expense", food_cat, checking, Decimal("920.00"), "Supermercado"),
            ("2026-02-12", "transfer", None, checking, Decimal("2000.00"), "Ahorro mensual"),
        ]

        for date, tx_type, category, account, amount, desc in sample_transactions:
            tx_hash = Transaction.compute_hash(user.pk, account.pk, date, amount, desc)
            if not Transaction.objects.filter(user=user, content_hash=tx_hash).exists():
                tx = Transaction(
                    user=user,
                    account=account,
                    category=category,
                    transaction_type=tx_type,
                    amount=amount,
                    description=desc,
                    date=date,
                )
                if tx_type == "transfer":
                    tx.transfer_to_account = savings
                tx.save()

        Debt.objects.get_or_create(
            user=user,
            nombre="Préstamo personal",
            defaults={
                "prestamista": "Banco Nacional",
                "monto_requerido": Decimal("5000000.00"),
                "monto_pagado": Decimal("1500000.00"),
                "fecha_limite": "2026-12-31",
                "observaciones": "Préstamo a 12 meses",
            },
        )
        Debt.objects.get_or_create(
            user=user,
            nombre="Deuda familiar",
            defaults={
                "prestamista": "Mamá",
                "monto_requerido": Decimal("800000.00"),
                "monto_pagado": Decimal("800000.00"),
                "fecha_limite": "2026-03-01",
                "observaciones": "Ya pagada",
            },
        )

        Goal.objects.get_or_create(
            user=user,
            nombre="Viaje a Japón",
            defaults={
                "monto_requerido": Decimal("5000000.00"),
                "monto_abonado": Decimal("1500000.00"),
                "fecha_limite": "2026-12-31",
                "observaciones": "Meta de ahorro para vacaciones",
            },
        )
        Goal.objects.get_or_create(
            user=user,
            nombre="Fondo de emergencia",
            defaults={
                "monto_requerido": Decimal("2000000.00"),
                "monto_abonado": Decimal("2000000.00"),
                "fecha_limite": "2026-06-01",
                "observaciones": "Meta completada",
            },
        )

        # Usuarios extra para probar el módulo de Contactos (búsqueda y relación
        # bidireccional). Idempotentes, misma contraseña que el usuario demo.
        juan, juan_created = User.objects.get_or_create(
            email="juan@fintrack.local",
            defaults={
                "username": "juan",
                "first_name": "Juan",
                "last_name": "Pérez",
            },
        )
        if juan_created:
            juan.set_password("demo1234")
            juan.save()
        maria, maria_created = User.objects.get_or_create(
            email="maria@fintrack.local",
            defaults={
                "username": "maria",
                "first_name": "María",
                "last_name": "Gómez",
            },
        )
        if maria_created:
            maria.set_password("demo1234")
            maria.save()
        add_contact(user, juan)
        add_contact(user, maria)

        # Grupo demo con el contacto Juan como integrante (add es idempotente).
        grupo, _ = ContactGroup.objects.get_or_create(
            user=user,
            name="Viaje Cartagena",
            defaults={"description": "Gastos del viaje a Cartagena"},
        )
        contacto_juan = Contact.objects.get(user=user, contact=juan)
        contacto_maria = Contact.objects.get(user=user, contact=maria)
        grupo.members.add(contacto_juan)

        # Gasto compartido demo: el dueño paga, Juan y María son participantes,
        # con un pago parcial de Juan ya registrado.
        if not SharedExpense.objects.filter(user=user, name="Cena grupo Cartagena").exists():
            specs = build_participant_specs(True, [contacto_juan, contacto_maria])
            shared_expense = create_shared_expense(
                user=user,
                name="Cena grupo Cartagena",
                description="Cena del viaje a Cartagena",
                account=checking,
                category=food_cat,
                date="2026-02-20",
                total_amount=Decimal("150000.00"),
                participant_specs=specs,
                payer_spec=ParticipantSpec(True, None),
            )
            juan_participant = shared_expense.participants.get(contact=contacto_juan)
            register_shared_expense_payment(
                participant=juan_participant,
                amount=Decimal("20000.00"),
                date="2026-02-25",
                notes="Abono parcial",
                account=checking,
            )

        # Segundo gasto demo: pagó un contacto (Juan), no el dueño. No genera
        # ninguna Transacción de gasto — es puramente informativo.
        if not SharedExpense.objects.filter(user=user, name="Peaje pagado por Juan").exists():
            specs_juan_paga = build_participant_specs(True, [contacto_juan])
            juan_spec = next(s for s in specs_juan_paga if s.contact == contacto_juan)
            peaje = create_shared_expense(
                user=user,
                name="Peaje pagado por Juan",
                description="Juan adelantó el peaje del viaje",
                account=None,
                category=transport_cat,
                date="2026-02-18",
                total_amount=Decimal("30000.00"),
                participant_specs=specs_juan_paga,
                payer_spec=juan_spec,
            )
            # El dueño salda su propia parte: sí genera una Transacción de gasto real.
            owner_participant_peaje = peaje.participants.get(is_owner=True)
            register_shared_expense_payment(
                participant=owner_participant_peaje,
                amount=Decimal("15000.00"),
                date="2026-02-22",
                notes="Le pagué a Juan mi parte del peaje",
                account=checking,
            )

        self.load_monthly_history(
            user, checking, savings, salary_cat, food_cat, transport_cat,
            contacto_juan, contacto_maria,
        )
        self.stdout.write(self.style.SUCCESS("Datos de demostración cargados correctamente."))

    def load_monthly_history(
        self, user, checking, savings, salary_cat, food_cat, transport_cat,
        contacto_juan, contacto_maria,
    ):
        """Carga doce meses móviles sin duplicar ni modificar registros existentes."""
        today = timezone.localdate()
        housing, _ = Category.objects.get_or_create(
            user=user, name="Vivienda", category_type="expense",
            defaults={"color": "#8b5cf6"},
        )
        utilities, _ = Category.objects.get_or_create(
            user=user, name="Servicios", category_type="expense",
            defaults={"color": "#06b6d4"},
        )
        freelance, _ = Category.objects.get_or_create(
            user=user, name="Trabajo independiente", category_type="income",
            defaults={"color": "#10b981"},
        )
        recurrent = Tag.objects.get(user=user, name="recurrente")
        current = today.replace(day=1)
        months = []
        for _ in range(12):
            months.insert(0, current)
            current = (current - timedelta(days=1)).replace(day=1)

        added = 0
        for index, month in enumerate(months):
            label = month.strftime("%Y-%m")
            rows = [
                (1, "income", salary_cat, "3800000", "Salario"),
                (3, "expense", housing, "1200000", "Arriendo"),
                (5, "expense", food_cat, str(420000 + index * 5000), "Mercado"),
                (8, "expense", utilities, str(210000 + index * 2000), "Servicios e internet"),
                (10, "expense", transport_cat, str(160000 + index * 3000), "Transporte mensual"),
                (12, "transfer", None, "400000", "Transferencia a ahorros"),
                (15, "income", freelance, str(300000 + index * 25000), "Proyecto independiente"),
                (18, "expense", food_cat, str(85000 + index * 1500), "Restaurante"),
                (21, "expense", transport_cat, "60000", "Recarga de transporte"),
            ]
            for day, kind, category, amount, description in rows:
                tx_date = month.replace(day=day)
                if tx_date > today:
                    continue
                description = f"{description} · demo {label}"
                amount = Decimal(amount).quantize(Decimal("0.01"))
                content_hash = Transaction.compute_hash(
                    user.pk, checking.pk, tx_date, amount, description
                )
                tx, created = Transaction.objects.get_or_create(
                    user=user, content_hash=content_hash,
                    defaults={
                        "account": checking, "category": category,
                        "transaction_type": kind, "amount": amount,
                        "description": description, "date": tx_date,
                        "transfer_to_account": savings if kind == "transfer" else None,
                        "notes": "Movimiento de demostración mensual en COP.",
                    },
                )
                if created:
                    tx.tags.add(recurrent)
                    added += 1
            for category, amount in [(food_cat, "650000"), (transport_cat, "300000"), (utilities, "300000")]:
                Budget.objects.get_or_create(
                    user=user, category=category, period_start=month,
                    period_end=month.replace(day=monthrange(month.year, month.month)[1]),
                    defaults={"amount": Decimal(amount), "notes": "Presupuesto mensual demo"},
                )

        specs = build_participant_specs(True, [contacto_juan, contacto_maria])
        for title, status in [("Almuerzo del equipo", "pendiente"), ("Compra para reunión", "parcial"), ("Salida de fin de semana", "completado")]:
            name = f"{title} · demo {today:%Y-%m}"
            if SharedExpense.objects.filter(user=user, name=name).exists():
                continue
            expense = create_shared_expense(
                user=user, name=name, description="Ejemplo del mes actual",
                account=checking, category=food_cat, date=today.replace(day=1),
                total_amount=Decimal("90000.00"), participant_specs=specs,
                payer_spec=specs[0],
            )
            for participant in expense.participants.exclude(is_owner=True):
                if status == "completado" or (status == "parcial" and participant.contact_id == contacto_juan.pk):
                    register_shared_expense_payment(
                        participant=participant,
                        amount=participant.amount_pending if status == "completado" else Decimal("10000.00"),
                        date=today.replace(day=1), account=checking,
                    )

        Debt.objects.get_or_create(
            user=user, nombre="Crédito educativo · demo",
            defaults={"prestamista": "Cooperativa", "monto_requerido": Decimal("2400000"),
                      "monto_pagado": Decimal("600000"), "fecha_limite": today + timedelta(days=15)},
        )
        Goal.objects.get_or_create(
            user=user, nombre="Renovar computador · demo",
            defaults={"monto_requerido": Decimal("4500000"), "monto_abonado": Decimal("1800000"),
                      "fecha_limite": today + timedelta(days=180)},
        )
        self.stdout.write(f"Historial mensual: {added} movimientos nuevos; 12 meses de presupuestos.")
