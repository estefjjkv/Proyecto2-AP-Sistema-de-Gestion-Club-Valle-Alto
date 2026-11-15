from getpass import getpass
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from accounts.models import Administrator, AdminRole
from accounts.validators import normalize_id

class Command(BaseCommand):
    help = "Crea un administrador GENERAL en la tabla administrador (no crea un socio)."
    def handle(self, **options):
        try:
            role=AdminRole.objects.get(pk="GENERAL")
            person=Administrator(cedula=normalize_id(input("Cédula: ")), nombre_completo=input("Nombre completo: ").strip(), email=input("Correo: ").strip().lower(), rol=role)
            password=getpass("Contraseña: ")
            if password!=getpass("Repita la contraseña: "): raise CommandError("Las contraseñas no coinciden.")
            validate_password(password,person)
            person.set_password(password)
            person.full_clean()
            with transaction.atomic(): person.save(force_insert=True)
        except (ValidationError, IntegrityError) as error: raise CommandError(str(error))
        self.stdout.write(self.style.SUCCESS("Administrador creado. Ingrese seleccionando Personal administrativo."))
