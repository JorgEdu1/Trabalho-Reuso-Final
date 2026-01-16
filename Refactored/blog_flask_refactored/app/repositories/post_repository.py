from app.extensions import db
from app.models.posts import Blog_Posts
# Precisamos importar os models para deletá-los
from app.models.comments import Blog_Comments, Blog_Replies
from app.models.likes import Blog_Likes
from app.models.bookmarks import Blog_Bookmarks

class PostRepository:
    @staticmethod
    def get_by_id(post_id):
        return Blog_Posts.query.get_or_404(post_id)

    @staticmethod
    def add(post):
        try:
            db.session.add(post)
            db.session.commit()
            return post
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def update():
        """Apenas confirma as mudanças feitas nos objetos carregados."""
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def delete_with_cascade(post):
        """
        Deleta o post e limpa manualmente todas as dependências no banco.
        Isso substitui a lógica espalhada na rota antiga.
        """
        try:
            # 1. Deletar Likes
            likes = Blog_Likes.query.filter_by(post_id=post.id).all()
            for like in likes:
                db.session.delete(like)

            # 2. Deletar Bookmarks
            bookmarks = Blog_Bookmarks.query.filter_by(post_id=post.id).all()
            for bm in bookmarks:
                db.session.delete(bm)

            # 3. Deletar Comentários e Respostas
            comments = Blog_Comments.query.filter_by(post_id=post.id).all()
            for comment in comments:
                replies = Blog_Replies.query.filter_by(comment_id=comment.id).all()
                for reply in replies:
                    db.session.delete(reply)
                db.session.delete(comment)

            # 4. Deletar o Post
            db.session.delete(post)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e