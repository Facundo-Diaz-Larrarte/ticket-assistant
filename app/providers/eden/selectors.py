"""Selectores semánticos y tolerantes para el flujo de compra en Eden Entradas."""

# Botón principal de compra en la página del evento
BUY_BUTTONS = [
    'button:has-text("COMPRAR")',
    'button:has-text("Comprar")',
    'button:has-text("COMPRAR ENTRADAS")',
    'a:has-text("COMPRAR")',
    '.btn-primary.next',
    '#picker button',
    '.action_picker .btn-primary'
]

# Selector de sectores / ubicaciones
SECTOR_CONTAINERS = [
    '.sectors-list',
    '.pricing-table',
    '.ticket-types',
    '#sector_list'
]

# Botón para continuar o agregar al carrito
CONTINUE_BUTTONS = [
    'button:has-text("Continuar")',
    'button:has-text("CONTINUAR")',
    'button:has-text("Siguiente")',
    '#btn-continue',
    '.checkout-actions button'
]

# Campos del formulario de comprador
BUYER_FORM = {
    "first_name": ['input[name="firstName"]', 'input[name="first_name"]', '#first_name'],
    "last_name": ['input[name="lastName"]', 'input[name="last_name"]', '#last_name'],
    "dni": ['input[name="document"]', 'input[name="dni"]', '#dni', '#document'],
    "email": ['input[name="email"]', '#email', 'input[type="email"]'],
    "phone": ['input[name="phone"]', 'input[name="cellphone"]', '#phone']
}

# Indicadores de Human Checkpoint (Detención de Seguridad)
HUMAN_CHECKPOINT_INDICATORS = [
    'iframe[src*="mercadopago"]',
    'iframe[src*="decidir"]',
    'iframe[src*="modo"]',
    '#page-captcha',
    '.payment-box',
    'text="Número de tarjeta"',
    'text="Código de seguridad"',
    'text="3D Secure"',
    'text="Validación de compra"'
]
