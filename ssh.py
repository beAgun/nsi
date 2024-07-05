import os.path
from pprint import pprint
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import paramiko
from ssh_config import DATABASES
from test_semd.configuration import documents_mapping
from test_semd.tests import TestSEMD


test = TestSEMD(medDocumentType=['41'], currentStatus=['4'], org_db_alias=['p17'])
pprint(test.test_cases)

for test, lpu in test.test_cases:
    if "organization" not in DATABASES[lpu]:  # not SPb
        print('no org')
        continue

    DATABASE_CONFIG = DATABASES[lpu]
    DATABASE_URI = f"{DATABASE_CONFIG['engine']}://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}?charset={DATABASE_CONFIG['charset']}"

    engine = create_engine(DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    if test.get('action_id'):
        stmt = """
        SELECT deleted, file_path from SignedIEMKDocument WHERE event_id = {event_id} AND action_id = {action_id} 
        AND deleted = 0;
        """.format(event_id=test.get('event_id'), action_id=test.get('action_id'))
    else:
        stmt = """
        SELECT deleted, file_path from SignedIEMKDocument WHERE event_id = {event_id} 
        AND deleted = 0;
        """.format(event_id=test.get('event_id'))

    record = session.connection().execute(stmt).fetchone()
    if not record.file_path:
        print(stmt)
        print()
        continue
    remote_path = record.file_path
    local_path = f'/home/vista/xml_files/{remote_path.split("/")[-1]}'

    if os.path.isfile(local_path):
        continue

    # Установите соединение с сервером
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(lpu, username='root', password='shedF34A')

    # Используйте sftp для передачи файлов
    sftp = ssh.open_sftp()



    # Скачайте файл
    try:
        sftp.get(remote_path, local_path)
    except FileNotFoundError as e:
        print(e, remote_path, stmt, sep='\n')
        print()

    # Закройте соединения
    sftp.close()
    ssh.close()
