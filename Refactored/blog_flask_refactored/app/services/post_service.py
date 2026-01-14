import os
from flask import current_app
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.posts import Blog_Posts
from app.dashboard.helpers import check_blog_picture

class PostService:
    @staticmethod
    def create_post_entry(form, author_id):
        """Cria o registro do post no banco de dados (sem as imagens inicialmente)."""
        try:
            post = Blog_Posts(
                theme_id=form.theme.data,
                date_to_post=form.date.data,
                title=form.title.data,
                intro=form.intro.data,
                body=form.body.data,
                picture_v_source=form.picture_v_source.data,
                picture_h_source=form.picture_h_source.data,
                picture_s_source=form.picture_s_source.data,
                picture_alt=form.picture_alt.data,
                meta_tag=form.meta_tag.data,
                title_tag=form.title_tag.data,
                author_id=author_id
            )
            db.session.add(post)
            db.session.commit()
            return post
        except Exception as e:
            db.session.rollback()
            return None

    @staticmethod
    def handle_post_images(post, form, request_files):
        """Processa o upload das 3 imagens (v, h, s). Retorna flags de sucesso/erro."""
        img_status = {'missing': False, 'error': False}
        
        # Lista de formatos para iterar e evitar repetição de código
        formats = [
            ('v', form.picture_v, form.picture_v_size),
            ('h', form.picture_h, form.picture_h_size),
            ('s', form.picture_s, form.picture_s_size)
        ]

        for suffix, field_data, field_size in formats:
            # Lógica de verificação se a imagem foi enviada e tamanho ok
            if field_data.data and int(field_size.data) < 1500000:
                filename = secure_filename(field_data.data.filename)
                success = PostService._save_single_image(post, filename, suffix, request_files)
                if not success:
                    img_status['error'] = True
            else:
                img_status['missing'] = True
        
        return img_status

    @staticmethod
    def _save_single_image(post, filename, suffix, request_files):
        """Método auxiliar privado para salvar uma única imagem."""
        try:
            new_img_name = check_blog_picture(post.id, filename, suffix)
            if new_img_name:
                file_key = f"picture_{suffix}"
                file_obj = request_files[file_key]
                
                # Salva no disco
                save_path = os.path.join(current_app.config["BLOG_IMG_FOLDER"], new_img_name)
                file_obj.save(save_path)
                
                # Atualiza referência no objeto post
                if suffix == 'v': post.picture_v = new_img_name
                elif suffix == 'h': post.picture_h = new_img_name
                elif suffix == 's': post.picture_s = new_img_name
                
                db.session.commit()
                return True
        except Exception:
            return False
        return False