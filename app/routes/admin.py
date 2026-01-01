File "/opt/venv/lib/python3.12/site-packages/gunicorn/arbiter.py", line 609, in spawn_worker
worker.init_process()
File "/opt/venv/lib/python3.12/site-packages/gunicorn/workers/gthread.py", line 95, in init_process
super().init_process()
File "/opt/venv/lib/python3.12/site-packages/gunicorn/workers/base.py", line 134, in init_process
self.load_wsgi()
File "/opt/venv/lib/python3.12/site-packages/gunicorn/workers/base.py", line 146, in load_wsgi
self.wsgi = self.app.wsgi()
^^^^^^^^^^^^^^^
File "/opt/venv/lib/python3.12/site-packages/gunicorn/app/base.py", line 67, in wsgi
self.callable = self.load()
^^^^^^^^^^^
File "/opt/venv/lib/python3.12/site-packages/gunicorn/app/wsgiapp.py", line 58, in load
return self.load_wsgiapp()
^^^^^^^^^^^^^^^^^^^
File "/opt/venv/lib/python3.12/site-packages/gunicorn/app/wsgiapp.py", line 48, in load_wsgiapp
return util.import_app(self.app_uri)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/opt/venv/lib/python3.12/site-packages/gunicorn/util.py", line 371, in import_app
mod = importlib.import_module(module)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/root/.nix-profile/lib/python3.12/importlib/__init__.py", line 90, in import_module
return _bootstrap._gcd_import(name[level:], package, level)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "", line 1387, in _gcd_import
File "", line 1360, in _find_and_load
File "", line 1331, in _find_and_load_unlocked
File "", line 935, in _load_unlocked
File "", line 995, in exec_module
File "", line 488, in _call_with_frames_removed
File "/app/run.py", line 19, in 
app = create_app(get_config())
^^^^^^^^^^^^^^^^^^^^^^^^
File "/app/app/__init__.py", line 47, in create_app
register_blueprints(app)
File "/app/app/__init__.py", line 139, in register_blueprints
from app.routes.auth import auth_bp
File "/app/app/routes/__init__.py", line 6, in 
from app.routes.admin import admin_bp
File "/app/app/routes/admin.py", line 1
{% extends "base.html" %}
^
SyntaxError: invalid syntax
[2026-01-01 18:47:03 +0000] [10] [INFO] Worker exiting (pid: 10)
[2026-01-01 18:47:03,645] INFO in websocket: Flask-SocketIO initialized with manage_session=True
2026-01-01 18:47:03,645 - app.utils.websocket - INFO - Flask-SocketIO initialized with manage_session=True
[2026-01-01 18:47:03,645] INFO in extensions: ✅ Flask-SocketIO initialized
2026-01-01 18:47:03,645 - app - INFO - ✅ Flask-SocketIO initialized
[2026-01-01 18:47:03 +0000] [12] [ERROR] Exception in worker process
Traceback (most recent call last):
File "/opt/venv/lib/python3.12/site-packages/gunicorn/arbiter.py", line 609, in spawn_worker
worker.init_process()
File "/opt/venv/lib/python3.12/site-packages/gunicorn/workers/gthread.py", line 95, in init_process
super().init_process()
File "/opt/venv/lib/python3.12/site-packages/gunicorn/workers/base.py", line 134, in init_process
self.load_wsgi()
File "/opt/venv/lib/python3.12/site-packages/gunicorn/workers/base.py", line 146, in load_wsgi
self.wsgi = self.app.wsgi()
^^^^^^^^^^^^^^^
File "/opt/venv/lib/python3.12/site-packages/gunicorn/app/base.py", line 67, in wsgi
self.callable = self.load()
^^^^^^^^^^^
File "/opt/venv/lib/python3.12/site-packages/gunicorn/app/wsgiapp.py", line 58, in load
return self.load_wsgiapp()
^^^^^^^^^^^^^^^^^^^
File "/opt/venv/lib/python3.12/site-packages/gunicorn/app/wsgiapp.py", line 48, in load_wsgiapp
return util.import_app(self.app_uri)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/opt/venv/lib/python3.12/site-packages/gunicorn/util.py", line 371, in import_app
mod = importlib.import_module(module)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/root/.nix-profile/lib/python3.12/importlib/__init__.py", line 90, in import_module
return _bootstrap._gcd_import(name[level:], package, level)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "", line 1387, in _gcd_import
File "", line 1360, in _find_and_load
File "", line 1331, in _find_and_load_unlocked
File "", line 935, in _load_unlocked
File "", line 995, in exec_module
File "", line 488, in _call_with_frames_removed
File "/app/run.py", line 19, in 
app = create_app(get_config())
^^^^^^^^^^^^^^^^^^^^^^^^
File "/app/app/__init__.py", line 47, in create_app
register_blueprints(app)
File "/app/app/__init__.py", line 139, in register_blueprints
from app.routes.auth import auth_bp
File "/app/app/routes/__init__.py", line 6, in 
from app.routes.admin import admin_bp
File "/app/app/routes/admin.py", line 1
{% extends "base.html" %}
^
SyntaxError: invalid syntax
[2026-01-01 18:47:03 +0000] [12] [INFO] Worker exiting (pid: 12)
[2026-01-01 18:47:03 +0000] [1] [ERROR] Worker (pid:9) exited with code 3
[2026-01-01 18:47:03 +0000] [1] [ERROR] Worker (pid:11) was sent SIGTERM!
[2026-01-01 18:47:03 +0000] [1] [ERROR] Worker (pid:10) was sent SIGTERM!
[2026-01-01 18:47:03 +0000] [1] [ERROR] Worker (pid:12) was sent SIGTERM!
[2026-01-01 18:47:03 +0000] [1] [ERROR] Shutting down: Master
[2026-01-01 18:47:03 +0000] [1] [ERROR] Reason: Worker failed to boot.
