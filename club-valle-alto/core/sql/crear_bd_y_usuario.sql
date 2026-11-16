-- =====================================================================
-- Club Valle Alto - Crear usuario y base de datos (se ejecuta UNA vez)
--
-- Ejecutar conectado como superusuario (postgres), por ejemplo:
--   psql -U postgres -f core/sql/crear_bd_y_usuario.sql
-- o pegarlo en el Query Tool de pgAdmin (conectado a la BD "postgres").
--
-- Use la misma contraseña que puso en DB_PASSWORD del archivo .env.
-- Las tablas NO se crean aquí: las crea "python manage.py migrate".
-- =====================================================================

CREATE ROLE club_admin WITH LOGIN PASSWORD 'REEMPLAZAR_POR_CLAVE_PRIVADA';

CREATE DATABASE club_valle_alto
    OWNER club_admin
    ENCODING 'UTF8'
    TEMPLATE template0;

-- Para que "python manage.py test" pueda crear la BD de pruebas:
ALTER ROLE club_admin CREATEDB;
