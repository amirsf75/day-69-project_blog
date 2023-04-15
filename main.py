from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
# from sqlalchemy.ext.declarative import declarative_base
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps
from flask import abort


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

login_manager = LoginManager()
login_manager.init_app(app)


gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


# #CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# #CONFIGURE TABLES

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)

    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship('BlogPost', back_populates="author")

    # *******Add parent relationship*******#
    # "comment_author" refers to the comment_author property in the Comment class.
    comments = relationship('Comment', back_populates="comment_author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    # author = db.Column(db.String(250), nullable=False)  for relation we don't need this
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # child of user
    author = relationship("User", back_populates="posts")
    # parent for comments
    comments = relationship("Comment", back_populates="parent_post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'))

    # child of user
    comment_author = relationship("User", back_populates="comments")
    # child of blogpost
    parent_post = relationship("BlogPost", back_populates="comments")


with app.app_context():
    db.create_all()


# Create admin-only decorator
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If id is not 1 then return abort with 403 error
        if current_user.id != 1:
            return abort(403)
        # Otherwise continue with the route function
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, logged_in=current_user.is_authenticated)


@app.route('/register', methods=["POST", "GET"])
def register():
    form = RegisterForm()
    if request.method == "POST":
        if not User.query.filter_by(email=request.form.get("email")).first():  # email doesn't exist
            new_user = User(email=request.form.get('email'),
                            password=generate_password_hash(request.form.get('password'), 'pbkdf2:sha256', 6),
                            name=request.form.get('name'))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('get_all_posts'))
        else:
            flash("This email exist Try to log in")
            return redirect(url_for('login'))

    return render_template("register.html", form=form, logged_in=current_user.is_authenticated)


@app.route('/login', methods=["POST", "GET"])
def login():
    form = LoginForm()
    if request.method == "POST":
        selected_user = User.query.filter_by(email=request.form.get("email")).first()

        if selected_user:  # user exist
            if check_password_hash(selected_user.password, request.form.get("password")):
                login_user(selected_user)
                return redirect(url_for('get_all_posts'))
            else:
                flash("Wrong password")
                return redirect(url_for("login"))
        else:
            flash("email not found , Please Register")
            return redirect(url_for("register"))
    return render_template("login.html", form=form, logged_in=current_user.is_authenticated)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["POST", "GET"])
def show_post(post_id):
    form = CommentForm()

    if request.method == "POST":
        if current_user.is_authenticated:  # user logged in
            new_comment = Comment(text=request.form.get("comment_text"),
                                  comment_author=current_user,
                                  parent_post=BlogPost.query.get(post_id))
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for("show_post", post_id=post_id))

        else:
            flash("Please register Or Loging To send comment")
            return redirect(url_for("login"))

    requested_post = BlogPost.query.get(post_id)
    # post_comments = Comment.query.filter_by(post_id=post_id).all()  # NOT NEED
    return render_template("post.html", post=requested_post, logged_in=current_user.is_authenticated, form=form)


@app.route("/about")
def about():
    return render_template("about.html", logged_in=current_user.is_authenticated)


@app.route("/contact")
def contact():
    return render_template("contact.html", logged_in=current_user.is_authenticated)


@app.route("/new-post", methods=["POST", "GET"])
@login_required
@admin_only
def add_new_post():
    form = CreatePostForm()

    if request.method == "POST":
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))

    return render_template("make-post.html", form=form, logged_in=current_user.is_authenticated)


@app.route("/edit-post/<int:post_id>", methods=["POST", "GET"])
@login_required
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if request.method == "POST":
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        # post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, logged_in=current_user.is_authenticated)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)
