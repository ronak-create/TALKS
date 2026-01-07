from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    bio = db.Column(db.String)
    contact = db.Column(db.String)
    google_id = db.Column(db.String)

    posts = db.relationship('Post', back_populates='user', cascade='all, delete-orphan')
    comments = db.relationship('Comment', back_populates='user', cascade='all, delete-orphan')
    post_likes = db.relationship('PostLike', back_populates='user', cascade='all, delete-orphan')
    comment_likes = db.relationship('CommentLike', back_populates='user', cascade='all, delete-orphan')


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='posts')
    comments = db.relationship('Comment', back_populates='post', cascade='all, delete-orphan')
    likes = db.relationship('PostLike', back_populates='post', cascade='all, delete-orphan')
    reports = db.relationship('Report', back_populates='post', cascade='all, delete-orphan')


class PostLike(db.Model):
    __tablename__ = 'post_likes'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    post = db.relationship('Post', back_populates='likes')
    user = db.relationship('User', back_populates='post_likes')


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    post = db.relationship('Post', back_populates='comments')
    user = db.relationship('User', back_populates='comments')
    likes = db.relationship('CommentLike', back_populates='comment', cascade='all, delete-orphan')


class CommentLike(db.Model):
    __tablename__ = 'comment_likes'
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    comment = db.relationship('Comment', back_populates='likes')
    user = db.relationship('User', back_populates='comment_likes')


class Report(db.Model):
    __tablename__ = 'reports'
    report_id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    status = db.Column(db.String, default='Pending')
    reported_at = db.Column(db.DateTime, default=datetime.utcnow)

    post = db.relationship('Post', back_populates='reports')


class UserQuery(db.Model):
    __tablename__ = 'user_queries'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False)
    message = db.Column(db.Text, nullable=False)


class Hashtag(db.Model):
    __tablename__ = 'hashtags'
    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String, unique=True)
    count = db.Column(db.Integer, default=1)
    post_ids = db.Column(db.Text)  # Can store JSON-encoded list of post IDs


class EmailVerification(db.Model):
    __tablename__ = 'email_verifications'
    email = db.Column(db.String, primary_key=True)
    code = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
