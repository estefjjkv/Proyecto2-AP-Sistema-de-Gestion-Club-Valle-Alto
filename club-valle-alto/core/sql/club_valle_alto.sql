-- =====================================================================
-- Club Valle Alto - Sistema de gestión (IC-4810, II semestre 2026)
-- Base de datos PostgreSQL
--
-- Criterios de diseño:
--  * PK naturales siempre que existan (cédula, código de catálogo,
--    (socio, periodo), etc.). Cuando la PK es también FK no hay id extra.
--  * Solo se usa IDENTITY donde no hay identificador natural razonable:
--    reserva, cargo, notificacion, bloqueo_instalacion.
--  * Catálogos con PK = código textual corto (legible, estable).
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS btree_gist;   -- para evitar traslapes de reservas

-- =====================================================================
-- 1. CATÁLOGOS
-- =====================================================================

CREATE TABLE cat_estado_cuenta_socio (
    codigo       varchar(20) PRIMARY KEY,
    descripcion  varchar(100) NOT NULL
);

CREATE TABLE cat_tipo_membresia (
    codigo                 varchar(20) PRIMARY KEY,
    descripcion            varchar(100) NOT NULL,
    cuota_base             numeric(12,2) NOT NULL CHECK (cuota_base >= 0),
    limite_beneficiarios   smallint NOT NULL DEFAULT 0 CHECK (limite_beneficiarios >= 0),
    limite_invitados_mes   smallint NOT NULL DEFAULT 0 CHECK (limite_invitados_mes >= 0)
);

CREATE TABLE cat_estado_membresia (
    codigo       varchar(20) PRIMARY KEY,
    descripcion  varchar(100) NOT NULL
);

CREATE TABLE cat_parentesco (
    codigo       varchar(20) PRIMARY KEY,
    descripcion  varchar(100) NOT NULL
);

CREATE TABLE cat_relacion_invitado (
    codigo       varchar(20) PRIMARY KEY,
    descripcion  varchar(100) NOT NULL
);

CREATE TABLE cat_tipo_instalacion (
    codigo       varchar(20) PRIMARY KEY,
    descripcion  varchar(100) NOT NULL
);

CREATE TABLE cat_estado_reserva (
    codigo       varchar(20) PRIMARY KEY,
    descripcion  varchar(100) NOT NULL
);

CREATE TABLE cat_motivo_bloqueo (
    codigo       varchar(20) PRIMARY KEY,
    descripcion  varchar(100) NOT NULL
);

CREATE TABLE cat_rol_admin (
    codigo       varchar(20) PRIMARY KEY,
    descripcion  varchar(100) NOT NULL
);

CREATE TABLE cat_permiso (
    codigo       varchar(40) PRIMARY KEY,
    descripcion  varchar(150) NOT NULL
);

CREATE TABLE cat_tipo_cargo (
    codigo       varchar(30) PRIMARY KEY,
    descripcion  varchar(100) NOT NULL
);

CREATE TABLE cat_estado_cargo (
    codigo       varchar(20) PRIMARY KEY,
    descripcion  varchar(100) NOT NULL
);

CREATE TABLE cat_tipo_notificacion (
    codigo       varchar(40) PRIMARY KEY,
    descripcion  varchar(150) NOT NULL
);

CREATE TABLE cat_estado_envio (
    codigo       varchar(20) PRIMARY KEY,
    descripcion  varchar(100) NOT NULL
);

-- ---------------------------------------------------------------------
-- Datos iniciales de catálogos
-- (cuotas y límites son valores de ejemplo: ajustar al reglamento del club)
-- ---------------------------------------------------------------------
INSERT INTO cat_estado_cuenta_socio VALUES
    ('ACTIVA',      'Cuenta activa'),
    ('SUSPENDIDA',  'Cuenta suspendida por un administrador'),
    ('DESACTIVADA', 'Cuenta desactivada');

INSERT INTO cat_tipo_membresia
    (codigo, descripcion, cuota_base, limite_beneficiarios, limite_invitados_mes) VALUES
    ('INDIVIDUAL',  'Membresía individual',  50000, 0, 4),
    ('FAMILIAR',    'Membresía familiar',    90000, 5, 8),
    ('CORPORATIVA', 'Membresía corporativa', 150000, 0, 12),
    ('HONORARIA',   'Membresía honoraria',   0,     0, 10);

INSERT INTO cat_estado_membresia VALUES
    ('ACTIVA',     'Membresía activa'),
    ('SUSPENDIDA', 'Membresía suspendida'),
    ('VENCIDA',    'Membresía vencida'),
    ('BAJA',       'Membresía dada de baja');

INSERT INTO cat_parentesco VALUES
    ('CONYUGE', 'Cónyuge'),
    ('HIJO',    'Hijo/a'),
    ('PADRE',   'Padre/Madre'),
    ('HERMANO', 'Hermano/a'),
    ('OTRO',    'Otro');

INSERT INTO cat_relacion_invitado VALUES
    ('FAMILIAR', 'Familiar'),
    ('AMIGO',    'Amigo/a'),
    ('OTRO',     'Otro');

INSERT INTO cat_tipo_instalacion VALUES
    ('GOLF',          'Cancha de golf'),
    ('TENIS',         'Cancha de tenis'),
    ('PISCINA',       'Piscina'),
    ('SALON_EVENTOS', 'Salón de eventos');

INSERT INTO cat_estado_reserva VALUES
    ('PENDIENTE',  'Solicitada, pendiente de confirmación'),
    ('CONFIRMADA', 'Confirmada'),
    ('CANCELADA',  'Cancelada'),
    ('FINALIZADA', 'Finalizada');

INSERT INTO cat_motivo_bloqueo VALUES
    ('MANTENIMIENTO',  'Mantenimiento de la instalación'),
    ('EVENTO_PRIVADO', 'Evento privado');

INSERT INTO cat_rol_admin VALUES
    ('GENERAL',       'Administrador general'),
    ('INSTALACIONES', 'Encargado de instalaciones'),
    ('COBROS',        'Encargado de cobros');

INSERT INTO cat_permiso VALUES
    ('GESTIONAR_SOCIOS',        'Ver, activar, suspender y desactivar socios; restablecer contraseñas'),
    ('GESTIONAR_MEMBRESIAS',    'Crear, modificar, suspender y dar de baja membresías'),
    ('GESTIONAR_INSTALACIONES', 'Calendario, reservas, bloqueos y reportes de uso'),
    ('CONSULTAR_INVITADOS',     'Consultar invitados esperados por día'),
    ('GESTIONAR_COBROS',        'Estados de cuenta, registro de pagos y morosos'),
    ('GESTIONAR_PLANTILLAS',    'Editar plantillas de notificación'),
    ('CONSULTAR_NOTIFICACIONES','Consultar historial de notificaciones'),
    ('GESTIONAR_ADMINS',        'Crear y modificar usuarios administradores');

INSERT INTO cat_tipo_cargo VALUES
    ('CUOTA_MEMBRESIA',    'Cuota de membresía'),
    ('SERVICIO_ADICIONAL', 'Servicio adicional de una reserva');

INSERT INTO cat_estado_cargo VALUES
    ('PENDIENTE', 'Pendiente de pago'),
    ('PAGADO',    'Pagado'),
    ('VENCIDO',   'Vencido');

INSERT INTO cat_tipo_notificacion VALUES
    ('NUEVO_SOCIO',        'Registro de un nuevo socio'),
    ('RESERVA_CONFIRMADA', 'Confirmación de reserva'),
    ('RESERVA_MODIFICADA', 'Modificación de reserva'),
    ('RESERVA_CANCELADA',  'Cancelación de reserva'),
    ('NUEVO_ESTADO_CUENTA','Generación de un nuevo estado de cuenta'),
    ('PAGO_POR_VENCER',    'Recordatorio de pago próximo a vencer'),
    ('PAGO_VENCIDO',       'Recordatorio de pago vencido');

INSERT INTO cat_estado_envio VALUES
    ('PENDIENTE', 'En cola de envío'),
    ('ENVIADA',   'Enviada'),
    ('FALLIDA',   'Falló el envío');

-- =====================================================================
-- 2. ADMINISTRADORES Y PERMISOS
-- =====================================================================

CREATE TABLE rol_permiso (
    codigo_rol      varchar(20) NOT NULL REFERENCES cat_rol_admin(codigo),
    codigo_permiso  varchar(40) NOT NULL REFERENCES cat_permiso(codigo),
    PRIMARY KEY (codigo_rol, codigo_permiso)
);

INSERT INTO rol_permiso (codigo_rol, codigo_permiso)
SELECT 'GENERAL', codigo FROM cat_permiso;

INSERT INTO rol_permiso VALUES
    ('INSTALACIONES', 'GESTIONAR_INSTALACIONES'),
    ('INSTALACIONES', 'CONSULTAR_INVITADOS'),
    ('COBROS',        'GESTIONAR_COBROS'),
    ('COBROS',        'CONSULTAR_NOTIFICACIONES');

CREATE TABLE administrador (
    cedula             varchar(20) PRIMARY KEY,
    nombre_completo    varchar(150) NOT NULL,
    correo             varchar(150) NOT NULL,
    codigo_rol         varchar(20) NOT NULL REFERENCES cat_rol_admin(codigo),
    password_hash      varchar(255) NOT NULL,
    activo             boolean NOT NULL DEFAULT true,
    intentos_fallidos  smallint NOT NULL DEFAULT 0 CHECK (intentos_fallidos >= 0),
    bloqueado_hasta    timestamptz,
    fecha_creacion     timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ux_administrador_correo ON administrador (lower(correo));

-- =====================================================================
-- 3. SOCIOS
-- =====================================================================

CREATE TABLE socio (
    cedula              varchar(20) PRIMARY KEY,
    nombre_completo     varchar(150) NOT NULL,
    correo              varchar(150) NOT NULL,
    telefono            varchar(20)  NOT NULL,
    direccion           varchar(300) NOT NULL,
    fecha_nacimiento    date NOT NULL CHECK (fecha_nacimiento < CURRENT_DATE),
    password_hash       varchar(255) NOT NULL,
    codigo_estado       varchar(20) NOT NULL DEFAULT 'ACTIVA'
                            REFERENCES cat_estado_cuenta_socio(codigo),
    intentos_fallidos   smallint NOT NULL DEFAULT 0 CHECK (intentos_fallidos >= 0),
    bloqueado_hasta     timestamptz,           -- bloqueo por intentos fallidos
    fecha_registro      timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ux_socio_correo ON socio (lower(correo));

-- Enlaces de recuperación de contraseña (se guarda el hash del token)
CREATE TABLE token_recuperacion (
    token_hash    varchar(64) PRIMARY KEY,
    cedula_socio  varchar(20) NOT NULL REFERENCES socio(cedula) ON DELETE CASCADE,
    fecha_expira  timestamptz NOT NULL,
    usado         boolean NOT NULL DEFAULT false,
    fecha_creado  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_token_recuperacion_socio ON token_recuperacion (cedula_socio);

-- =====================================================================
-- 4. MEMBRESÍAS
-- =====================================================================

-- Un socio tiene una membresía (PK = FK al socio, sin id adicional).
-- Los cambios de estado quedan en historial_membresia.
CREATE TABLE membresia (
    cedula_socio      varchar(20) PRIMARY KEY REFERENCES socio(cedula),
    codigo_tipo       varchar(20) NOT NULL REFERENCES cat_tipo_membresia(codigo),
    fecha_inscripcion date NOT NULL DEFAULT CURRENT_DATE,
    fecha_renovacion  date NOT NULL,
    monto_cuota       numeric(12,2) NOT NULL CHECK (monto_cuota >= 0),
    codigo_estado     varchar(20) NOT NULL DEFAULT 'ACTIVA'
                          REFERENCES cat_estado_membresia(codigo),
    CHECK (fecha_renovacion > fecha_inscripcion)
);

CREATE TABLE historial_membresia (
    cedula_socio      varchar(20) NOT NULL REFERENCES membresia(cedula_socio),
    -- clock_timestamp() (no now()): now() es fijo durante toda la transacción y
    -- dos cambios de estado en la misma transacción chocarían por PK duplicada.
    fecha_cambio      timestamptz NOT NULL DEFAULT clock_timestamp(),
    estado_anterior   varchar(20) REFERENCES cat_estado_membresia(codigo),
    estado_nuevo      varchar(20) NOT NULL REFERENCES cat_estado_membresia(codigo),
    cedula_admin      varchar(20) REFERENCES administrador(cedula),
    motivo            varchar(300),
    PRIMARY KEY (cedula_socio, fecha_cambio)
);

-- Beneficiarios de membresías familiares (PK compuesta natural)
CREATE TABLE beneficiario (
    cedula_titular       varchar(20) NOT NULL REFERENCES membresia(cedula_socio) ON DELETE CASCADE,
    cedula_beneficiario  varchar(20) NOT NULL,
    nombre_completo      varchar(150) NOT NULL,
    codigo_parentesco    varchar(20) NOT NULL REFERENCES cat_parentesco(codigo),
    fecha_nacimiento     date NOT NULL CHECK (fecha_nacimiento < CURRENT_DATE),
    PRIMARY KEY (cedula_titular, cedula_beneficiario),
    CHECK (cedula_titular <> cedula_beneficiario)
);

-- Registra automáticamente cada cambio de estado de una membresía
CREATE FUNCTION fn_historial_membresia() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO historial_membresia (cedula_socio, fecha_cambio, estado_anterior, estado_nuevo)
        VALUES (NEW.cedula_socio, clock_timestamp(), NULL, NEW.codigo_estado);
    ELSIF NEW.codigo_estado IS DISTINCT FROM OLD.codigo_estado THEN
        INSERT INTO historial_membresia (cedula_socio, fecha_cambio, estado_anterior, estado_nuevo)
        VALUES (NEW.cedula_socio, clock_timestamp(), OLD.codigo_estado, NEW.codigo_estado);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_historial_membresia
AFTER INSERT OR UPDATE OF codigo_estado ON membresia
FOR EACH ROW EXECUTE FUNCTION fn_historial_membresia();

-- Límite máximo de beneficiarios según el tipo de membresía
CREATE FUNCTION fn_validar_beneficiario() RETURNS trigger AS $$
DECLARE
    v_limite  smallint;
    v_actuales integer;
BEGIN
    SELECT t.limite_beneficiarios INTO v_limite
    FROM membresia m
    JOIN cat_tipo_membresia t ON t.codigo = m.codigo_tipo
    WHERE m.cedula_socio = NEW.cedula_titular;

    SELECT count(*) INTO v_actuales
    FROM beneficiario
    WHERE cedula_titular = NEW.cedula_titular
      AND cedula_beneficiario <> NEW.cedula_beneficiario;

    IF v_actuales >= v_limite THEN
        RAISE EXCEPTION 'La membresía solo permite % beneficiario(s)', v_limite
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_beneficiario
BEFORE INSERT OR UPDATE ON beneficiario
FOR EACH ROW EXECUTE FUNCTION fn_validar_beneficiario();

-- =====================================================================
-- 5. INSTALACIONES, SERVICIOS Y BLOQUEOS
-- =====================================================================

CREATE TABLE instalacion (
    codigo         varchar(30) PRIMARY KEY,           -- ej. 'TENIS-1', 'PISCINA-A'
    nombre         varchar(100) NOT NULL,
    codigo_tipo    varchar(20) NOT NULL REFERENCES cat_tipo_instalacion(codigo),
    aforo_maximo   integer NOT NULL CHECK (aforo_maximo > 0),
    hora_apertura  time NOT NULL,
    hora_cierre    time NOT NULL,
    activa         boolean NOT NULL DEFAULT true,
    CHECK (hora_cierre > hora_apertura)
);

-- Servicios adicionales (alquiler de equipo, montaje de mobiliario, etc.)
CREATE TABLE servicio_adicional (
    codigo               varchar(30) PRIMARY KEY,
    nombre               varchar(100) NOT NULL,
    descripcion          varchar(300),
    codigo_tipo_instalacion varchar(20) NOT NULL REFERENCES cat_tipo_instalacion(codigo),
    precio               numeric(12,2) NOT NULL CHECK (precio >= 0),
    activo               boolean NOT NULL DEFAULT true
);

-- Bloqueos por mantenimiento o eventos privados
CREATE TABLE bloqueo_instalacion (
    id_bloqueo          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo_instalacion  varchar(30) NOT NULL REFERENCES instalacion(codigo),
    inicio              timestamp NOT NULL,
    fin                 timestamp NOT NULL,
    codigo_motivo       varchar(20) NOT NULL REFERENCES cat_motivo_bloqueo(codigo),
    descripcion         varchar(300),
    cedula_admin        varchar(20) NOT NULL REFERENCES administrador(cedula),
    fecha_creacion      timestamptz NOT NULL DEFAULT now(),
    CHECK (fin > inicio),
    EXCLUDE USING gist (codigo_instalacion WITH =, tsrange(inicio, fin) WITH &&)
);

-- =====================================================================
-- 6. RESERVAS
-- =====================================================================

CREATE TABLE reserva (
    id_reserva          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cedula_socio        varchar(20) NOT NULL REFERENCES socio(cedula),
    codigo_instalacion  varchar(30) NOT NULL REFERENCES instalacion(codigo),
    fecha               date NOT NULL,
    hora_inicio         time NOT NULL,
    hora_fin            time NOT NULL,
    numero_personas     integer NOT NULL CHECK (numero_personas > 0),
    codigo_estado       varchar(20) NOT NULL DEFAULT 'PENDIENTE'
                            REFERENCES cat_estado_reserva(codigo),
    fecha_creacion      timestamptz NOT NULL DEFAULT now(),
    fecha_cancelacion   timestamptz,
    cedula_admin        varchar(20) REFERENCES administrador(cedula), -- quien confirmó/modificó/canceló
    rango               tsrange GENERATED ALWAYS AS
                            (tsrange(fecha + hora_inicio, fecha + hora_fin)) STORED,
    CHECK (hora_fin > hora_inicio),
    -- sin traslapes entre reservas vigentes de la misma instalación
    CONSTRAINT ex_reserva_sin_traslape
        EXCLUDE USING gist (codigo_instalacion WITH =, rango WITH &&)
        WHERE (codigo_estado IN ('PENDIENTE', 'CONFIRMADA'))
);
CREATE INDEX ix_reserva_socio ON reserva (cedula_socio, fecha);
CREATE INDEX ix_reserva_instalacion_fecha ON reserva (codigo_instalacion, fecha);

-- Servicios adicionales de la reserva (PK compuesta, sin id propio)
CREATE TABLE reserva_servicio (
    id_reserva       bigint NOT NULL REFERENCES reserva(id_reserva) ON DELETE CASCADE,
    codigo_servicio  varchar(30) NOT NULL REFERENCES servicio_adicional(codigo),
    cantidad         integer NOT NULL DEFAULT 1 CHECK (cantidad > 0),
    precio_unitario  numeric(12,2) NOT NULL CHECK (precio_unitario >= 0),  -- precio al reservar
    PRIMARY KEY (id_reserva, codigo_servicio)
);

-- Validaciones: horario de la instalación, aforo, bloqueos y membresía activa
CREATE FUNCTION fn_validar_reserva() RETURNS trigger AS $$
DECLARE
    v_inst  instalacion%ROWTYPE;
    v_ini   timestamp := NEW.fecha + NEW.hora_inicio;
    v_fin   timestamp := NEW.fecha + NEW.hora_fin;
BEGIN
    IF NEW.codigo_estado NOT IN ('PENDIENTE', 'CONFIRMADA') THEN
        RETURN NEW;
    END IF;

    SELECT * INTO v_inst FROM instalacion WHERE codigo = NEW.codigo_instalacion;

    IF NOT v_inst.activa THEN
        RAISE EXCEPTION 'La instalación % no está disponible', v_inst.codigo;
    END IF;
    IF NEW.hora_inicio < v_inst.hora_apertura OR NEW.hora_fin > v_inst.hora_cierre THEN
        RAISE EXCEPTION 'Horario fuera del rango de apertura (% - %)',
            v_inst.hora_apertura, v_inst.hora_cierre;
    END IF;
    IF NEW.numero_personas > v_inst.aforo_maximo THEN
        RAISE EXCEPTION 'Se excede el aforo máximo de % personas', v_inst.aforo_maximo;
    END IF;
    IF EXISTS (SELECT 1 FROM bloqueo_instalacion b
               WHERE b.codigo_instalacion = NEW.codigo_instalacion
                 AND tsrange(b.inicio, b.fin) && tsrange(v_ini, v_fin)) THEN
        RAISE EXCEPTION 'La instalación está bloqueada en ese horario';
    END IF;
    IF TG_OP = 'INSERT' AND NOT EXISTS (
           SELECT 1 FROM membresia m
           WHERE m.cedula_socio = NEW.cedula_socio AND m.codigo_estado = 'ACTIVA') THEN
        RAISE EXCEPTION 'El socio no tiene una membresía activa';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_reserva
BEFORE INSERT OR UPDATE ON reserva
FOR EACH ROW EXECUTE FUNCTION fn_validar_reserva();

-- =====================================================================
-- 7. INVITADOS
-- =====================================================================

CREATE TABLE invitado (
    cedula           varchar(20) PRIMARY KEY,
    nombre_completo  varchar(150) NOT NULL
);

-- Cada invitación: socio + invitado + fecha + instalación (clave natural)
CREATE TABLE invitacion (
    cedula_socio        varchar(20) NOT NULL REFERENCES socio(cedula),
    cedula_invitado     varchar(20) NOT NULL REFERENCES invitado(cedula),
    fecha_visita        date NOT NULL,
    codigo_instalacion  varchar(30) NOT NULL REFERENCES instalacion(codigo),
    codigo_relacion     varchar(20) NOT NULL REFERENCES cat_relacion_invitado(codigo),
    id_reserva          bigint REFERENCES reserva(id_reserva) ON DELETE SET NULL, -- opcional
    fecha_registro      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (cedula_socio, cedula_invitado, fecha_visita, codigo_instalacion),
    CHECK (cedula_socio <> cedula_invitado)
);
CREATE INDEX ix_invitacion_fecha ON invitacion (fecha_visita);   -- listado de recepción

-- Límite mensual de invitados según el tipo de membresía
CREATE FUNCTION fn_validar_limite_invitados() RETURNS trigger AS $$
DECLARE
    v_limite   smallint;
    v_usados   integer;
BEGIN
    SELECT t.limite_invitados_mes INTO v_limite
    FROM membresia m
    JOIN cat_tipo_membresia t ON t.codigo = m.codigo_tipo
    WHERE m.cedula_socio = NEW.cedula_socio AND m.codigo_estado = 'ACTIVA';

    IF v_limite IS NULL THEN
        RAISE EXCEPTION 'El socio no tiene una membresía activa';
    END IF;

    SELECT count(*) INTO v_usados
    FROM invitacion i
    WHERE i.cedula_socio = NEW.cedula_socio
      AND date_trunc('month', i.fecha_visita) = date_trunc('month', NEW.fecha_visita)
      AND NOT (TG_OP = 'UPDATE'
               AND i.cedula_invitado    = OLD.cedula_invitado
               AND i.fecha_visita       = OLD.fecha_visita
               AND i.codigo_instalacion = OLD.codigo_instalacion);

    IF v_usados >= v_limite THEN
        RAISE EXCEPTION 'Límite de % invitados por mes alcanzado', v_limite
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validar_limite_invitados
BEFORE INSERT OR UPDATE OF cedula_socio, fecha_visita ON invitacion
FOR EACH ROW EXECUTE FUNCTION fn_validar_limite_invitados();

-- =====================================================================
-- 8. ESTADO DE CUENTA
-- =====================================================================

-- Un estado de cuenta por socio y periodo (primer día del mes)
CREATE TABLE estado_cuenta (
    cedula_socio      varchar(20) NOT NULL REFERENCES socio(cedula),
    periodo           date NOT NULL CHECK (EXTRACT(day FROM periodo) = 1),
    fecha_generacion  timestamptz NOT NULL DEFAULT now(),
    fecha_limite_pago date NOT NULL,
    PRIMARY KEY (cedula_socio, periodo)
);

-- Rubros del estado de cuenta (cuota de membresía o servicios de reservas)
CREATE TABLE cargo (
    id_cargo          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cedula_socio      varchar(20) NOT NULL,
    periodo           date NOT NULL,
    codigo_tipo       varchar(30) NOT NULL REFERENCES cat_tipo_cargo(codigo),
    descripcion       varchar(200) NOT NULL,
    monto             numeric(12,2) NOT NULL CHECK (monto >= 0),
    fecha_limite_pago date NOT NULL,
    codigo_estado     varchar(20) NOT NULL DEFAULT 'PENDIENTE' REFERENCES cat_estado_cargo(codigo),
    fecha_pago        timestamptz,
    cedula_admin_pago varchar(20) REFERENCES administrador(cedula),  -- quien registró el pago
    id_reserva        bigint REFERENCES reserva(id_reserva) ON DELETE SET NULL,
    FOREIGN KEY (cedula_socio, periodo) REFERENCES estado_cuenta(cedula_socio, periodo),
    CHECK ((codigo_estado = 'PAGADO') = (fecha_pago IS NOT NULL))
);
CREATE INDEX ix_cargo_estado_cuenta ON cargo (cedula_socio, periodo);
CREATE INDEX ix_cargo_estado ON cargo (codigo_estado, fecha_limite_pago);

-- Marca como VENCIDOS los cargos pendientes cuya fecha límite ya pasó
-- (ejecutar a diario: pg_cron, tarea programada del backend, etc.)
CREATE FUNCTION fn_marcar_cargos_vencidos() RETURNS integer AS $$
DECLARE
    v_filas integer;
BEGIN
    UPDATE cargo
       SET codigo_estado = 'VENCIDO'
     WHERE codigo_estado = 'PENDIENTE'
       AND fecha_limite_pago < CURRENT_DATE;
    GET DIAGNOSTICS v_filas = ROW_COUNT;
    RETURN v_filas;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- 9. NOTIFICACIONES
-- =====================================================================

-- Plantilla editable por administrador: una por tipo de notificación
CREATE TABLE plantilla_notificacion (
    codigo_tipo         varchar(40) PRIMARY KEY REFERENCES cat_tipo_notificacion(codigo),
    asunto              varchar(200) NOT NULL,
    cuerpo              text NOT NULL,        -- admite marcadores, ej. {{nombre}}, {{fecha}}
    cedula_admin        varchar(20) REFERENCES administrador(cedula),
    fecha_actualizacion timestamptz NOT NULL DEFAULT now()
);

INSERT INTO plantilla_notificacion (codigo_tipo, asunto, cuerpo)
SELECT codigo,
       'Club Valle Alto - ' || descripcion,
       'Estimado/a {{nombre}}: ' || descripcion || '. Detalle: {{detalle}}.'
FROM cat_tipo_notificacion;

-- Historial de notificaciones enviadas
CREATE TABLE notificacion (
    id_notificacion  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cedula_socio     varchar(20) NOT NULL REFERENCES socio(cedula),
    codigo_tipo      varchar(40) NOT NULL REFERENCES cat_tipo_notificacion(codigo),
    correo_destino   varchar(150) NOT NULL,
    asunto           varchar(200) NOT NULL,
    cuerpo           text NOT NULL,
    codigo_estado    varchar(20) NOT NULL DEFAULT 'PENDIENTE' REFERENCES cat_estado_envio(codigo),
    id_reserva       bigint REFERENCES reserva(id_reserva) ON DELETE SET NULL,
    fecha_creacion   timestamptz NOT NULL DEFAULT now(),
    fecha_envio      timestamptz
);
CREATE INDEX ix_notificacion_socio ON notificacion (cedula_socio, fecha_creacion DESC);

-- =====================================================================
-- 10. VISTAS DE CONSULTA / REPORTES
-- =====================================================================

-- Resumen del estado de cuenta por socio y periodo
CREATE VIEW v_estado_cuenta_resumen AS
SELECT ec.cedula_socio,
       ec.periodo,
       ec.fecha_limite_pago,
       COALESCE(sum(c.monto), 0)                                           AS total,
       COALESCE(sum(c.monto) FILTER (WHERE c.codigo_estado = 'PAGADO'), 0)    AS pagado,
       COALESCE(sum(c.monto) FILTER (WHERE c.codigo_estado = 'PENDIENTE'), 0) AS pendiente,
       COALESCE(sum(c.monto) FILTER (WHERE c.codigo_estado = 'VENCIDO'), 0)   AS vencido
FROM estado_cuenta ec
LEFT JOIN cargo c ON c.cedula_socio = ec.cedula_socio AND c.periodo = ec.periodo
GROUP BY ec.cedula_socio, ec.periodo, ec.fecha_limite_pago;

-- Socios morosos según tiempo de atraso
CREATE VIEW v_socios_morosos AS
SELECT s.cedula,
       s.nombre_completo,
       s.correo,
       count(*)                                  AS cargos_atrasados,
       sum(c.monto)                              AS monto_adeudado,
       max(CURRENT_DATE - c.fecha_limite_pago)   AS dias_atraso_max
FROM cargo c
JOIN socio s ON s.cedula = c.cedula_socio
WHERE c.codigo_estado <> 'PAGADO'
  AND c.fecha_limite_pago < CURRENT_DATE
GROUP BY s.cedula, s.nombre_completo, s.correo;

-- Invitados esperados por día (recepción)
CREATE VIEW v_invitados_esperados AS
SELECT i.fecha_visita,
       i.codigo_instalacion,
       iv.cedula            AS cedula_invitado,
       iv.nombre_completo   AS nombre_invitado,
       i.codigo_relacion,
       s.cedula             AS cedula_socio,
       s.nombre_completo    AS nombre_socio
FROM invitacion i
JOIN invitado iv ON iv.cedula = i.cedula_invitado
JOIN socio s     ON s.cedula  = i.cedula_socio;

-- Uso de instalaciones por mes (demanda mayor/menor)
CREATE VIEW v_uso_instalaciones AS
SELECT r.codigo_instalacion,
       date_trunc('month', r.fecha)::date                       AS periodo,
       count(*)                                                 AS total_reservas,
       round(sum(EXTRACT(epoch FROM (r.hora_fin - r.hora_inicio)) / 3600)::numeric, 2) AS horas_reservadas,
       sum(r.numero_personas)                                   AS total_personas
FROM reserva r
WHERE r.codigo_estado IN ('CONFIRMADA', 'FINALIZADA')
GROUP BY r.codigo_instalacion, date_trunc('month', r.fecha);

-- Ocupación por franja horaria (monitoreo)
CREATE VIEW v_ocupacion_franja AS
SELECT r.codigo_instalacion,
       r.fecha,
       r.hora_inicio,
       r.hora_fin,
       r.numero_personas,
       i.aforo_maximo,
       round(100.0 * r.numero_personas / i.aforo_maximo, 1) AS porcentaje_ocupacion
FROM reserva r
JOIN instalacion i ON i.codigo = r.codigo_instalacion
WHERE r.codigo_estado IN ('PENDIENTE', 'CONFIRMADA');
