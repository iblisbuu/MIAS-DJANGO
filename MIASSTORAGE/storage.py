from googleapiclient import discovery,http
from oauth2client.client import GoogleCredentials
from operator import itemgetter
from tempfile import TemporaryFile
from io import BytesIO
from PIL import Image


def create_service():
    credentials = GoogleCredentials.get_application_default()
    return discovery.build('storage', 'v1', credentials=credentials)

def list_buckets(project):
    service = create_service()
    res = service.buckets().list(project=project,projection='full',fields='items(acl/entity,name)').execute()
    res['items'] = sorted(res['items'], key=itemgetter('name'))
    return res

def create_bucket(project, bucket_name):
    service = create_service()
    res = service.buckets().insert(
        project=project, body={
            "name": 'datacore_' + bucket_name,
            "acl":[{"entity": "allUsers","role": "WRITER"}],
            "defaultObjectAcl":[{"entity": "allUsers","role": "READER"}]
        }
    ).execute()
    return res

def delete_bucket(bucket_name):
    service = create_service()
    res = service.buckets().delete(bucket=bucket_name).execute()
    return res

def get_bucket(bucket_name):
    service = create_service()
    res = service.buckets().get(bucket=bucket_name).execute()
    return res

def list_objects(bucket):
    service = create_service()
    fields_to_return = \
        'nextPageToken,items(name,size,contentType,timeCreated,metadata(my-key))'
    req = service.objects().list(bucket=bucket, fields=fields_to_return)

    all_objects = []
    while req:
        resp = req.execute()
        all_objects.extend(resp.get('items', []))
        req = service.objects().list_next(req, resp)
    return all_objects

def create_object(bucket, filename, subdir):
	service = create_service()
	# body = {
	#     'name': subdir+'/'+filename.name,
	# }
	body = {
		'name': filename.name,
	}
	img = Image.open(filename)
	resized_image = img.resize((500, 700))
	img_bytes_data = BytesIO()
	resized_image.save(img_bytes_data, (filename.content_type).split('/')[1])
	temporary_file = TemporaryFile()
	temporary_file.write(img_bytes_data.getvalue())
	req = service.objects().insert(
		bucket=bucket, body=body,
		media_body=http.MediaIoBaseUpload(temporary_file, filename.content_type))
	resp = req.execute()
	temporary_file.close()
	return resp

def delete_object(bucket, filename):
    service = create_service()
    res = service.objects().delete(bucket=bucket, object=filename).execute()
    return res
