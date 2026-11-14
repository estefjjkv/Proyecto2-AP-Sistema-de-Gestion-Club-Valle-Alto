-- =====================================================================
-- Club Valle Alto - Reversa de club_valle_alto.sql
-- La usa la migración core.0001 al hacer: python manage.py migrate core zero
-- No elimina la extensión btree_gist (puede usarla otra base/esquema).
-- =====================================================================

DROP VIEW IF EXISTS
    v_ocupacion_franja,
    v_uso_instalaciones,
    v_invitados_esperados,
    v_socios_morosos,
    v_estado_cuenta_resumen;

DROP TABLE IF EXISTS
    notificacion,
    plantilla_notificacion,
    cargo,
    estado_cuenta,
    invitacion,
    invitado,
    reserva_servicio,
    reserva,
    bloqueo_instalacion,
    servicio_adicional,
    instalacion,
    beneficiario,
    historial_membresia,
    membresia,
    token_recuperacion,
    socio,
    administrador,
    rol_permiso,
    cat_estado_envio,
    cat_tipo_notificacion,
    cat_estado_cargo,
    cat_tipo_cargo,
    cat_permiso,
    cat_rol_admin,
    cat_motivo_bloqueo,
    cat_estado_reserva,
    cat_tipo_instalacion,
    cat_relacion_invitado,
    cat_parentesco,
    cat_estado_membresia,
    cat_tipo_membresia,
    cat_estado_cuenta_socio
CASCADE;

DROP FUNCTION IF EXISTS
    fn_marcar_cargos_vencidos(),
    fn_validar_limite_invitados(),
    fn_validar_reserva(),
    fn_validar_beneficiario(),
    fn_historial_membresia();
