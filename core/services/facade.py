from core.services.accounts import calculate_account_balance, get_user_total_balance
from core.services.credit_cards import (
    get_available_credit,
    get_next_payment_due_date,
    get_next_statement_date,
)
from core.services.reports import generate_transactions_pdf, get_category_distribution, get_monthly_income_expense
from core.services.csv_io import export_transactions_csv, import_transactions_csv
from core.services.payment_queue import build_payment_queue

class FinanceFacade:
    """Fachada única sobre los servicios de cuentas, tarjetas de crédito,
    reportes e import/export CSV, para que las vistas no dependan de conocer
    la organización interna de `core.services`."""

    def get_account_balance(self, account):
        return calculate_account_balance(account)

    def get_total_balance(self, user):
        return get_user_total_balance(user)

    def get_credit_info(self, account, details):
        return {
            "available": get_available_credit(account, details),
            "next_statement_date": get_next_statement_date(details),
            "next_due_date": get_next_payment_due_date(details),
        }

    def get_monthly_chart(self, user):
        return get_monthly_income_expense(user)

    def get_category_chart(self, user):
        return get_category_distribution(user)

    def export_csv(self, user):
        return export_transactions_csv(user)

    def import_csv(self, user, content):
        return import_transactions_csv(user, content)

    def generate_pdf(self, user):
        return generate_transactions_pdf(user)
    def get_payment_queue(self, user):
        return build_payment_queue(user)
