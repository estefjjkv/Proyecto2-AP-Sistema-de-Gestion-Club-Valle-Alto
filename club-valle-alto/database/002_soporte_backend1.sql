-- Complemento de integración Backend 1; el SQL original permanece intacto.
-- Reemplaza únicamente la función del historial, conservando su trigger.
CREATE OR REPLACE FUNCTION fn_historial_membresia() RETURNS trigger AS $$
DECLARE
    v_anterior varchar(20);
    v_fecha timestamptz;
BEGIN
    IF TG_OP = 'INSERT' THEN
        v_anterior := NULL;
    ELSIF NEW.codigo_estado IS DISTINCT FROM OLD.codigo_estado THEN
        v_anterior := OLD.codigo_estado;
    ELSE
        RETURN NEW;
    END IF;
    -- now() se repite dentro de una transacción; esta tabla usa la fecha como PK.
    SELECT GREATEST(clock_timestamp(), COALESCE(MAX(fecha_cambio) + interval '1 microsecond', '-infinity'::timestamptz))
    INTO v_fecha FROM historial_membresia WHERE cedula_socio = NEW.cedula_socio;
    INSERT INTO historial_membresia (cedula_socio,fecha_cambio,estado_anterior,estado_nuevo,cedula_admin,motivo)
    VALUES (NEW.cedula_socio,v_fecha,v_anterior,NEW.codigo_estado,
            NULLIF(current_setting('club.actor_admin',true),''),
            NULLIF(current_setting('club.motivo',true),''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

INSERT INTO cat_rol_admin(codigo,descripcion) VALUES ('RECEPCION','Recepción') ON CONFLICT DO NOTHING;
INSERT INTO rol_permiso(codigo_rol,codigo_permiso) VALUES ('RECEPCION','CONSULTAR_INVITADOS') ON CONFLICT DO NOTHING;
