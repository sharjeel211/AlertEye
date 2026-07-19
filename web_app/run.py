"""Run the AlertEye web portal."""
from dotenv import load_dotenv
load_dotenv()

from app import app, create_admin

if __name__ == '__main__':
    import os, traceback
    from flask import Response

    @app.errorhandler(Exception)
    def _log_unhandled(e):
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            return e
        tb = traceback.format_exc()
        try:
            with open(os.path.join(os.path.dirname(__file__), 'instance', 'last_error.txt'), 'w', encoding='utf-8') as f:
                f.write(tb)
        except Exception:
            pass
        print(tb)

        return Response('<pre>' + tb + '</pre>', status=500, mimetype='text/html')

    from app import APP_BUILD
    create_admin()
    print("\n🛡️  AlertEye Web Portal")
    print(f"   BUILD: {APP_BUILD}")
    print("   Admin: admin@alerteye.com / Admin@123")
    print("   URL:   http://localhost:5000\n")
    app.run(debug=False, host='0.0.0.0', port=5000)
