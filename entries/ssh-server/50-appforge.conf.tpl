# Generado por AppForge (receta ssh-server). Se sobrescribe al reaplicar.
Port $port
PermitRootLogin no
PasswordAuthentication $password_auth
KbdInteractiveAuthentication no
X11Forwarding no
MaxAuthTries 3
AllowUsers $APPFORGE_USER
