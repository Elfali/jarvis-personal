# Desplegar JARVIS en Oracle Cloud (guía paso a paso)

Guía concreta para Oracle Cloud. Si tu servidor es Ubuntu, el despliegue es un
solo comando. Tiempo total: unos 10 minutos.

## 1. Conéctate a tu servidor por SSH

En la consola de Oracle, en la instancia que creaste, copia su **IP pública**.

Abre la Terminal de tu Mac y entra:

```bash
ssh ubuntu@IP-PUBLICA
```

(En las instancias de Oracle Ubuntu el usuario por defecto es `ubuntu`. Si te
pide una clave, es la que descargaste al crear la instancia.)

## 2. Instala JARVIS

Dentro del servidor:

```bash
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/Elfali/jarvis-personal.git
cd jarvis-personal
sudo bash deploy/deploy.sh
```

El script hace **todo**: dependencias, entorno, contraseña aleatoria, servicio
que arranca solo, y abre el puerto en el cortafuegos del sistema.

Al terminar verás algo así:

```
============================================================
 JARVIS está en marcha.
   URL:        http://IP-PUBLICA:8765
   Contraseña: aB3xK9mQ2pL7wZ1c
============================================================
```

**Apunta esa contraseña.** Es la puerta de JARVIS.

## 3. Abre el puerto en la consola de Oracle (¡importante!)

Oracle bloquea todo el tráfico de entrada salvo SSH. Hay que abrir el puerto
`8765` también en su consola web (no basta con el cortafuegos del sistema):

1. Menú ☰ → **Networking** → **Virtual Cloud Networks**.
2. Entra en tu VCN → **Security Lists** → la lista por defecto.
3. **Add Ingress Rules** y rellena:
   - Source Type: `CIDR`
   - Source CIDR: `0.0.0.0/0`
   - IP Protocol: `TCP`
   - Destination Port Range: `8765`
4. **Add Ingress Rules**.

*(Truco: si pones `0.0.0.0/0` lo abres a todo internet. Más seguro: pon solo tu
IP de casa, si es fija.)*

## 4. Entra desde tu Mac

Abre en Chrome:

```
http://IP-PUBLICA:8765
```

Te pedirá la contraseña. La metes y ya tienes JARVIS.

Para tenerlo **como aplicación**: en Chrome, menú ⋮ → *Instalar JARVIS*.

## 5. El cerebro (opcional, pero recomendado)

Por defecto JARVIS intenta usar Ollama **dentro del servidor**, que no está
instalado. Dos caminos:

### A) Cerebro remoto (lo más fácil en un servidor sin GPU)

Consigue una clave gratuita en [Groq](https://console.groq.com) y edita el
`.env` del servidor:

```bash
nano ~/jarvis-personal/.env
```

```bash
JARVIS_BRAIN_PROVIDER=openai
JARVIS_BRAIN_BASE_URL=https://api.groq.com/openai/v1
JARVIS_BRAIN_MODEL=llama-3.3-70b-versatile
JARVIS_BRAIN_API_KEY=tu-clave-de-groq
```

Guarda (Ctrl+O, Enter, Ctrl+X) y reinicia:

```bash
sudo systemctl restart jarvis
```

### B) Ollama en el propio servidor

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2
```

Necesitas RAM suficiente (el plan gratuito de Oracle suele tenerla de sobra).

## 6. (Opcional) HTTPS y dominio

Para un candado y un nombre bonito, pon Caddy delante:

```bash
sudo apt-get install -y caddy
```

Y en `/etc/caddy/Caddyfile`:

```
tu-dominio.com {
    reverse_proxy localhost:8765
}
```

Caddy saca el certificado HTTPS solo.

## Comandos del día a día

```bash
sudo systemctl status jarvis     # ¿está vivo?
sudo systemctl restart jarvis    # reiniciar
sudo journalctl -u jarvis -f     # ver qué hace en vivo
```

## Actualizar JARVIS

```bash
cd ~/jarvis-personal
git pull
sudo systemctl restart jarvis
```

La memoria (lo aprendido) vive en `data/` y **no se toca** al actualizar.

## Seguridad

- La contraseña es obligatoria. No la quites ni la compartas.
- Idealmente, en la regla de entrada de Oracle limita el origen a tu IP.
- La voz (`edge-tts`) necesita que el servidor tenga salida a internet.
