from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import openai

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Clave secreta para las sesiones
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # Base de datos SQLite para almacenar usuarios e historial
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Configura tu clave de API de OpenAI
openai.api_key = "sk-proj-A73uWvv8IVfFvfG7MWBfT3BlbkFJs3mG2AQe427rd8P4BLUD"

# Modelo de Usuario
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    historial = db.relationship('Historial', backref='user', lazy=True)

# Modelo de Historial
class Historial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pregunta = db.Column(db.Text, nullable=False)
    respuesta = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Aquí envolvemos la creación de la base de datos en un contexto de aplicación
with app.app_context():
    db.create_all()  # Esto debería funcionar ahora

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Ruta para registrar usuarios
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('El correo ya está registrado.')
            return redirect(url_for('register'))
        
        new_user = User(email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registro exitoso, ahora puedes iniciar sesión.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# Ruta para iniciar sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Correo o contraseña incorrectos.')
    
    return render_template('login.html')

# Ruta para la página principal
@app.route('/')
@login_required
def home():
    # Al cargar la página, no se muestra el historial de mensajes actuales
    return render_template('index.html')

# Ruta para el historial
@app.route('/historial')
@login_required
def historial():
    historial = Historial.query.filter_by(user_id=current_user.id).all()
    return render_template('historial.html', historial=historial)

# Ruta para el chatbot
@app.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json()
    pregunta = data.get('pregunta', '')
    respuesta = procesar_consulta(pregunta)

    # Guardar pregunta y respuesta en el historial del usuario actual
    nuevo_historial = Historial(pregunta=pregunta, respuesta=respuesta, user_id=current_user.id)
    db.session.add(nuevo_historial)
    db.session.commit()
    
    return jsonify({"respuesta": respuesta})

# Función para verificar si la pregunta está relacionada con Linux
def es_pregunta_relevante(pregunta):
    temas_permitidos = ["linux", "unix", "bash", "terminal", "comandos", "sistema operativo"]
    return any(tema in pregunta.lower() for tema in temas_permitidos)

# Función para procesar la consulta
def procesar_consulta(pregunta):
    if not es_pregunta_relevante(pregunta):
        return "La pregunta no está relacionada con Linux. Intenta hacer preguntas sobre Linux."
    
    try:
        respuesta = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "Eres un experto en Linux. Responde solo preguntas relacionadas con Linux."},
                      {"role": "user", "content": pregunta}]
        )
        return respuesta['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"Error al procesar la solicitud: {e}"

# Ruta para cerrar sesión
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Has cerrado sesión con éxito.")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
