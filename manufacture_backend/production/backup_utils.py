import hashlib
import json
import os
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.db import connections
from django.utils import timezone


BACKUP_APP_ID = 'manufacture-system'
BACKUP_FORMAT_VERSION = 1
CONFIRM_RESTORE_TEXT = '我确认恢复备份'


class BackupError(Exception):
    pass


def _now_stamp():
    return timezone.localtime().strftime('%Y-%m-%d-%H%M%S')


def backup_filename(prefix='manufacture-backup'):
    return f'{prefix}-{_now_stamp()}.zip'


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_zip_member(zf, member_name):
    digest = hashlib.sha256()
    with zf.open(member_name, 'r') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_member_name(name):
    if not name or name.endswith('/'):
        return True
    posix_path = PurePosixPath(name)
    if posix_path.is_absolute() or '..' in posix_path.parts:
        return False
    return True


def _is_symlink(info):
    file_type = (info.external_attr >> 16) & 0o170000
    return file_type == stat.S_IFLNK


def _media_files():
    media_root = Path(settings.MEDIA_ROOT)
    if not media_root.exists():
        return []
    files = []
    for path in media_root.rglob('*'):
        if path.is_file() and not path.is_symlink():
            files.append(path)
    return sorted(files)


def _copy_sqlite_database(target_path):
    source_path = Path(settings.DATABASES['default']['NAME'])
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if not source_path.exists():
        raise BackupError(f'数据库文件不存在: {source_path}')

    connections.close_all()
    source = sqlite3.connect(str(source_path))
    try:
        backup = sqlite3.connect(str(target_path))
        try:
            source.backup(backup)
        finally:
            backup.close()
    finally:
        source.close()


def _build_manifest(db_copy_path, media_entries):
    db_stat = db_copy_path.stat()
    return {
        'app': BACKUP_APP_ID,
        'format_version': BACKUP_FORMAT_VERSION,
        'created_at': timezone.localtime().isoformat(),
        'database': {
            'path': 'db.sqlite3',
            'size': db_stat.st_size,
            'sha256': _sha256_file(db_copy_path),
        },
        'media': {
            'path': 'media/',
            'file_count': len(media_entries),
            'total_size': sum(item['size'] for item in media_entries),
            'files': media_entries,
        },
    }


def create_backup_archive(output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    media_root = Path(settings.MEDIA_ROOT)

    with tempfile.TemporaryDirectory(prefix='manufacture-backup-') as temp_dir:
        temp_dir = Path(temp_dir)
        db_copy_path = temp_dir / 'db.sqlite3'
        _copy_sqlite_database(db_copy_path)

        media_entries = []
        for path in _media_files():
            relative = path.relative_to(media_root).as_posix()
            archive_name = f'media/{relative}'
            media_entries.append({
                'path': archive_name,
                'size': path.stat().st_size,
                'sha256': _sha256_file(path),
            })

        manifest = _build_manifest(db_copy_path, media_entries)

        with zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                'manifest.json',
                json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8'),
            )
            zf.write(db_copy_path, 'db.sqlite3')
            for item in media_entries:
                source = media_root / item['path'][len('media/'):]
                zf.write(source, item['path'])

    return output_path


def create_temp_backup_archive():
    temp_dir = Path(tempfile.mkdtemp(prefix='manufacture-export-'))
    return create_backup_archive(temp_dir / backup_filename())


def cleanup_temp_backup(path):
    path = Path(path)
    root = path.parent
    try:
        shutil.rmtree(root)
    except OSError:
        pass


def _write_uploaded_file(file_obj, target_path):
    with open(target_path, 'wb') as target:
        if hasattr(file_obj, 'chunks'):
            for chunk in file_obj.chunks():
                target.write(chunk)
        else:
            for chunk in iter(lambda: file_obj.read(1024 * 1024), b''):
                target.write(chunk)


def _read_manifest(zf):
    try:
        raw = zf.read('manifest.json')
    except KeyError as exc:
        raise BackupError('备份包缺少 manifest.json') from exc
    try:
        manifest = json.loads(raw.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackupError('manifest.json 格式不正确') from exc

    if manifest.get('app') != BACKUP_APP_ID:
        raise BackupError('备份包不是当前系统生成的备份')
    if manifest.get('format_version') != BACKUP_FORMAT_VERSION:
        raise BackupError('备份包版本不兼容')
    return manifest


def _validate_zip_members(zf):
    for info in zf.infolist():
        if not _safe_member_name(info.filename):
            raise BackupError(f'备份包包含不安全路径: {info.filename}')
        if _is_symlink(info):
            raise BackupError(f'备份包包含不允许的符号链接: {info.filename}')


def _verify_manifest_hashes(zf, manifest):
    names = set(zf.namelist())
    if 'db.sqlite3' not in names:
        raise BackupError('备份包缺少 db.sqlite3')

    db_info = manifest.get('database') or {}
    if db_info.get('path') != 'db.sqlite3':
        raise BackupError('manifest 中数据库路径不正确')
    if int(db_info.get('size', -1)) != zf.getinfo('db.sqlite3').file_size:
        raise BackupError('数据库文件大小与 manifest 不一致')
    if db_info.get('sha256') != _sha256_zip_member(zf, 'db.sqlite3'):
        raise BackupError('数据库文件校验失败')

    media = manifest.get('media') or {}
    media_files = media.get('files') or []
    declared_media_paths = set()
    for item in media_files:
        member_path = item.get('path')
        if not member_path or not member_path.startswith('media/'):
            raise BackupError('manifest 中 media 文件路径不正确')
        if member_path not in names:
            raise BackupError(f'备份包缺少附件文件: {member_path}')
        declared_media_paths.add(member_path)
        if int(item.get('size', -1)) != zf.getinfo(member_path).file_size:
            raise BackupError(f'附件文件大小与 manifest 不一致: {member_path}')
        if item.get('sha256') != _sha256_zip_member(zf, member_path):
            raise BackupError(f'附件文件校验失败: {member_path}')

    actual_media_paths = {name for name in names if name.startswith('media/') and not name.endswith('/')}
    if declared_media_paths != actual_media_paths:
        raise BackupError('media 文件清单与备份包内容不一致')
    if int(media.get('file_count', -1)) != len(media_files):
        raise BackupError('附件文件数量与 manifest 不一致')
    if int(media.get('total_size', -1)) != sum(int(item.get('size', 0)) for item in media_files):
        raise BackupError('附件总大小与 manifest 不一致')


def _validate_sqlite_file(db_path):
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            result = conn.execute('PRAGMA quick_check').fetchone()
        finally:
            conn.close()
    except sqlite3.DatabaseError as exc:
        raise BackupError('db.sqlite3 不是有效的 SQLite 数据库') from exc
    if not result or result[0] != 'ok':
        raise BackupError('SQLite 数据库完整性检查失败')


def inspect_backup_archive(file_obj):
    with tempfile.TemporaryDirectory(prefix='manufacture-inspect-') as temp_dir:
        temp_dir = Path(temp_dir)
        zip_path = temp_dir / 'uploaded-backup.zip'
        _write_uploaded_file(file_obj, zip_path)

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                _validate_zip_members(zf)
                manifest = _read_manifest(zf)
                _verify_manifest_hashes(zf, manifest)
                db_path = temp_dir / 'db.sqlite3'
                with zf.open('db.sqlite3', 'r') as source, open(db_path, 'wb') as target:
                    shutil.copyfileobj(source, target)
                _validate_sqlite_file(db_path)
        except zipfile.BadZipFile as exc:
            raise BackupError('上传文件不是有效的 ZIP 备份包') from exc

        return {
            'created_at': manifest.get('created_at'),
            'database_size': manifest['database']['size'],
            'database_sha256': manifest['database']['sha256'],
            'media_file_count': manifest['media']['file_count'],
            'media_total_size': manifest['media']['total_size'],
            'format_version': manifest.get('format_version'),
        }


def _extract_backup_to_staging(file_obj, staging_dir):
    staging_dir = Path(staging_dir)
    upload_path = staging_dir / 'uploaded-backup.zip'
    _write_uploaded_file(file_obj, upload_path)

    try:
        with zipfile.ZipFile(upload_path, 'r') as zf:
            _validate_zip_members(zf)
            manifest = _read_manifest(zf)
            _verify_manifest_hashes(zf, manifest)
            zf.extract('db.sqlite3', staging_dir)
            for name in zf.namelist():
                if name.startswith('media/') and not name.endswith('/'):
                    zf.extract(name, staging_dir)
    except zipfile.BadZipFile as exc:
        raise BackupError('上传文件不是有效的 ZIP 备份包') from exc

    db_path = staging_dir / 'db.sqlite3'
    _validate_sqlite_file(db_path)
    return manifest


def restore_backup_archive(file_obj):
    db_path = Path(settings.DATABASES['default']['NAME'])
    media_root = Path(settings.MEDIA_ROOT)
    backups_dir = Path(settings.BASE_DIR) / 'backups'
    pre_backup_path = backups_dir / backup_filename('pre-restore')
    create_backup_archive(pre_backup_path)

    with tempfile.TemporaryDirectory(prefix='manufacture-restore-') as temp_dir:
        staging_dir = Path(temp_dir) / 'staging'
        staging_dir.mkdir(parents=True, exist_ok=True)
        manifest = _extract_backup_to_staging(file_obj, staging_dir)

        old_db_path = Path(temp_dir) / 'old-db.sqlite3'
        old_media_path = Path(temp_dir) / 'old-media'
        new_media_path = staging_dir / 'media'

        connections.close_all()
        if db_path.exists():
            shutil.copy2(db_path, old_db_path)
        if media_root.exists():
            shutil.copytree(media_root, old_media_path)

        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(staging_dir / 'db.sqlite3', db_path)

            if media_root.exists():
                shutil.rmtree(media_root)
            if new_media_path.exists():
                shutil.copytree(new_media_path, media_root)
            else:
                media_root.mkdir(parents=True, exist_ok=True)
        except Exception:
            connections.close_all()
            if old_db_path.exists():
                shutil.copy2(old_db_path, db_path)
            if media_root.exists():
                shutil.rmtree(media_root)
            if old_media_path.exists():
                shutil.copytree(old_media_path, media_root)
            raise
        finally:
            connections.close_all()

    return {
        'message': '恢复完成',
        'pre_restore_backup': str(pre_backup_path),
        'restored_created_at': manifest.get('created_at'),
        'restored_at': datetime.now().isoformat(),
    }
