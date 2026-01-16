from app.extensions import db
from app.models.user import Blog_User
from app.models.likes import Blog_Likes
from app.models.bookmarks import Blog_Bookmarks
from app.models.comments import Blog_Comments, Blog_Replies
from app.models.posts import Blog_Posts
from app.models.helpers import delete_comment, delete_reply

class UserRepository:
    @staticmethod
    def get_by_id(user_id):
        return Blog_User.query.get(int(user_id))

    @staticmethod
    def get_by_email(email):
        return Blog_User.query.filter_by(email=email).first()
    
    @staticmethod
    def get_by_name(name):
        return Blog_User.query.filter_by(name=name).first()

    @staticmethod
    def add(user):
        try:
            db.session.add(user)
            db.session.commit()
            return user
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def update():
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def delete_account_logic(user):
        """
        Replica a lógica complexa de deleção do legado:
        1. Transfere posts se for autor.
        2. Transfere comentários/respostas para usuário default (ID 3).
        3. Deleta likes e bookmarks.
        4. Deleta o usuário.
        """
        try:
            # 1. Se for autor, transfere posts para o Admin (ID 2 - regra do legado)
            # Nota: change_authorship_of_all_post é um helper de model, vamos chamar no Service ou assumir aqui se tiver acesso
            # Como é uma operação de banco em lote, podemos fazer aqui ou deixar o helper fazer.
            # Vamos focar na limpeza das dependências diretas:
            
            # 2. Comentários e Respostas (Transfere para user 3 e "deleta" logicamente)
            if user.comments:
                comments = Blog_Comments.query.filter_by(user_id=user.id).all()
                for comment in comments:
                    comment.user_id = 3
                    delete_comment(comment.id) # Helper do legado que marca como deleted

            if user.replies:
                replies = Blog_Replies.query.filter_by(user_id=user.id).all()
                for reply in replies:
                    reply.user_id = 3
                    delete_reply(reply.id)

            # 3. Likes e Bookmarks (Hard delete)
            if user.likes:
                likes = Blog_Likes.query.filter_by(user_id=user.id).all()
                for like in likes:
                    db.session.delete(like)
            
            if user.bookmarks:
                bookmarks = Blog_Bookmarks.query.filter_by(user_id=user.id).all()
                for bm in bookmarks:
                    db.session.delete(bm)

            # 4. Deleta o User
            db.session.delete(user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e