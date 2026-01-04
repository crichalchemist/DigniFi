"""Custom encrypted field types for intake models."""

from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from encrypted_model_fields.fields import EncryptedCharField


class EncryptedDecimalField(EncryptedCharField):
    """
    Encrypted field that stores Decimal values as encrypted strings.

    Provides field-level encryption for sensitive financial data (account balances,
    debt amounts) on top of PostgreSQL's encryption-at-rest.
    """

    description = "An encrypted decimal field"

    def __init__(self, max_digits=None, decimal_places=None, *args, **kwargs):
        self.max_digits = max_digits
        self.decimal_places = decimal_places
        # Set max_length to accommodate largest possible decimal as string
        # e.g., 12 digits + 2 decimal places + decimal point + sign = 15 chars
        if max_digits:
            kwargs['max_length'] = max_digits + 10  # Extra buffer for sign, decimal point
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        """Convert encrypted string from database to Decimal."""
        if value is None:
            return value
        # Parent class handles decryption
        decrypted = super().from_db_value(value, expression, connection)
        if decrypted == '' or decrypted is None:
            return None
        try:
            return Decimal(decrypted)
        except (InvalidOperation, ValueError):
            return None

    def to_python(self, value):
        """Convert value to Decimal for Python usage."""
        if value is None or value == '':
            return None
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        # Decrypt if needed
        decrypted = super().to_python(value)
        if decrypted == '' or decrypted is None:
            return None
        try:
            return Decimal(decrypted)
        except (InvalidOperation, ValueError) as e:
            raise ValidationError(f"Invalid decimal value: {e}")

    def get_prep_value(self, value):
        """Convert Decimal to string for encryption and storage."""
        if value is None:
            return None
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        # Convert to string for encryption
        return super().get_prep_value(str(value))

    def deconstruct(self):
        """For migrations."""
        name, path, args, kwargs = super().deconstruct()
        if self.max_digits is not None:
            kwargs['max_digits'] = self.max_digits
        if self.decimal_places is not None:
            kwargs['decimal_places'] = self.decimal_places
        return name, path, args, kwargs
