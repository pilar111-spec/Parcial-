from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
from functools import wraps 
app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'

# Configuración de la base de datos
def get_db_connection():
    conn = sqlite3.connect('blog.db')
    conn.row_factory = sqlite3.Row
    return conn

# Crear tablas si no existen
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# Rutas de autenticación
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if not username or not password:
            flash('Username y password son requeridos')
            return redirect(url_for('register'))
        
        password_hash = generate_password_hash(password)
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            conn = get_db_connection()
            conn.execute('INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)',
                        (username, password_hash, created_at))
            conn.commit()
            conn.close()
            flash('Registro exitoso. Por favor inicia sesión.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('El nombre de usuario ya existe')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Inicio de sesión exitoso')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión')
    return redirect(url_for('index'))

# Rutas del blog
@app.route('/')
def index():
    conn = get_db_connection()
    posts = conn.execute("""
        SELECT posts.id, posts.title, posts.content, posts.created_at, 
               users.username as author 
        FROM posts 
        JOIN users ON posts.user_id = users.id
        ORDER BY posts.created_at DESC
    """).fetchall()
    conn.close()

    return render_template('index.html', posts=posts)

@app.route('/dashboard')

def dashboard():
    conn = get_db_connection()
    # Obtener solo los posts del usuario actual
    user_posts = conn.execute('''
        SELECT * FROM posts 
        WHERE user_id = ?
        ORDER BY created_at DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('dashboard.html', posts=user_posts)

@app.route('/create_post', methods=['GET', 'POST'])

def create_post():
    if 'user_id' not in session:
        flash('Por favor inicia sesión para crear posts')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        
        if not title or not content:
            flash('Título y contenido son requeridos')
            return redirect(url_for('create_post'))
        
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn = get_db_connection()
        conn.execute('INSERT INTO posts (title, content, user_id, created_at) VALUES (?, ?, ?, ?)',
                    (title, content, session['user_id'], created_at))
        conn.commit()
        conn.close()
        flash('Post creado exitosamente')
        return redirect(url_for('dashboard'))
    
    return render_template('create_post.html')

@app.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    if 'user_id' not in session:
        flash('Por favor inicia sesión para editar posts')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    
    if post is None or post['user_id'] != session['user_id']:
        conn.close()
        flash('No tienes permiso para editar este post')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        
        if not title or not content:
            flash('Título y contenido son requeridos')
            return redirect(url_for('edit_post', post_id=post_id))
        
        conn.execute('UPDATE posts SET title = ?, content = ? WHERE id = ?',
                    (title, content, post_id))
        conn.commit()
        conn.close()
        flash('Post actualizado exitosamente')
        return redirect(url_for('dashboard'))
    
    conn.close()
    return render_template('edit_post.html', post=post)

@app.route('/delete_post/<int:post_id>')
def delete_post(post_id):
    if 'user_id' not in session:
        flash('Por favor inicia sesión para eliminar posts')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    
    if post is None or post['user_id'] != session['user_id']:
        conn.close()
        flash('No tienes permiso para eliminar este post')
        return redirect(url_for('dashboard'))
    
    conn.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    conn.commit()
    conn.close()
    flash('Post eliminado exitosamente')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)