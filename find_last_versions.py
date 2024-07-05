from pprint import pprint
from nsi_validation.config import engine
from sqlalchemy.orm import sessionmaker
from nsi_validation.nsi_parsing import NSIClient, RequestHandler

Session = sessionmaker(bind=engine)
session = Session()

stmt = "select * from NSI_Mapping"
ref_books = session.execute(stmt).fetchall()

request_handler = RequestHandler(verify_ssl=False)
nsi_client = NSIClient(request_handler)

for rb in ref_books:
    last_version = nsi_client.get_last_reference_book_version(
        rb.OID if not rb.additional_oid else rb.additional_oid
    )

    # stmt = f"SELECT * FROM NSIRefBooks WHERE OID = '{rb.OID}';"
    if last_version:
        stmt = (f"update NSI_Mapping set last_version = '{last_version}' "
                f"where OID = '{rb.OID}' and version = '{rb.version}';")
        try:
            session = Session()
            res = session.execute(stmt).rowcount
            session.commit()
            print(f'Stmt execution, {res} row updated')
        except Exception as e:
            print(e)
        finally:
            session.close()
    else:
        print(f'{rb.OID}, {rb.version}')