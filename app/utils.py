from flask import render_template, session, request
import logging

logger = logging.getLogger(__name__)

def register_error_handlers(app):
    @app.errorhandler(403)
    def forbidden(error):
        from app.logging_utils import log_security_event
        log_security_event('ACCESS_FORBIDDEN', {'requested_url': request.url}, 'WARNING')
        return render_template('errors/access_denied.html'), 403

    @app.errorhandler(404)
    def not_found(error):
        from app.logging_utils import log_security_event
        log_security_event('PAGE_NOT_FOUND', {'requested_url': request.url}, 'WARNING')
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        from app.logging_utils import log_security_event
        log_security_event('INTERNAL_ERROR', {'error': str(error)}, 'ERROR')
        logger.error(f"Internal server error: {error}")
        return render_template('errors/500.html'), 500

def inject_user_context():
    """Inject user information into all templates"""
    from app.auth.decorators import has_role
    return {
        'current_user': {
            'id': session.get('user_id'),
            'email': session.get('email'),
            'type': session.get('user_type')
        },
        'has_role': has_role
    }