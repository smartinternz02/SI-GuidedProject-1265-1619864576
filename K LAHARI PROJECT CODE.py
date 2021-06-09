import cv2
import time
import datetime
import ibm_boto3
from ibm_botocore.client import Config, ClientError
from ibmcloudant.cloudant_v1 import CloudantV1
from ibmcloudant import CouchDbSessionAuthenticator
from ibm_cloud_sdk_core.authenticators import BasicAuthenticator
import wiotp.sdk.device
# Constants for IBM COS values
COS_ENDPOINT = "https://manohar.s3.jp-tok.cloud-object-storage.appdomain.cloud" # Current list avaiable at https://control.cloud-object-storage.cloud.ibm.com/v2/endpoints
COS_API_KEY_ID = "67MBwu0H49L21goGQBII-SufzagQ-j-Lc-1xIRZOyqat" # eg "W00YixxxxxxxxxxMB-odB-2ySfTrFBIQQWanc--P3byk"
COS_INSTANCE_CRN = "crn:v1:bluemix:public:cloud-object-storage:global:a/94a9058de7634a75b86a721e2524a404:9eaeda1b-4ff4-4fa1-94a8-9917e79c2fc3::"

# Create resource
cos = ibm_boto3.resource("s3",
    ibm_api_key_id=COS_API_KEY_ID,
    ibm_service_instance_id=COS_INSTANCE_CRN,
    config=Config(signature_version="oauth"),
    endpoint_url=COS_ENDPOINT
)

authenticator = BasicAuthenticator('apikey-v2-2y8twpk3cni02ngsc297oqatoulogdt961768upuw79q', '43c3fef46c4ca6560b7359d05c4c3d57')
service = CloudantV1(authenticator=authenticator)
service.set_service_url('https://apikey-v2-2y8twpk3cni02ngsc297oqatoulogdt961768upuw79q:43c3fef46c4ca6560b7359d05c4c3d57@7b88ba8a-383b-49c5-ba00-9a03115de98a-bluemix.cloudantnosqldb.appdomain.cloud')

def myCommandCallback(cmd):
    print("Command received: %s" % cmd.data)


myConfig = { 
    "identity": {
        "orgId": "sn7dm1",
        "typeId": "ESP32",
        "deviceId": "1234599"
    },
    "auth": {
        "token": "9390569334"
    }
}
client = wiotp.sdk.device.DeviceClient(config=myConfig, logHandlers=None)
client.connect()

bucket = "manohar"
def multi_part_upload(bucket_name, item_name, file_path):
    try:
        print("Starting file transfer for {0} to bucket: {1}\n".format(item_name, bucket_name))
        # set 5 MB chunks
        part_size = 1024 * 1024 * 5

        # set threadhold to 15 MB
        file_threshold = 1024 * 1024 * 15

        # set the transfer threshold and chunk size
        transfer_config = ibm_boto3.s3.transfer.TransferConfig(
            multipart_threshold=file_threshold,
            multipart_chunksize=part_size
        )

        # the upload_fileobj method will automatically execute a multi-part upload
        # in 5 MB chunks for all files over 15 MB
        with open(file_path, "rb") as file_data:
            cos.Object(bucket_name, item_name).upload_fileobj(
                Fileobj=file_data,
                Config=transfer_config
            )

        print("Transfer for {0} Complete!\n".format(item_name))
    except ClientError as be:
        print("CLIENT ERROR: {0}\n".format(be))
    except Exception as e:
        print("Unable to complete multi-part upload: {0}".format(e))



face_classifier=cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
eye_classifier=cv2.CascadeClassifier("haarcascade_eye.xml")
#It will read the first frame/image of the video
video=cv2.VideoCapture("worker.mp4")

while True:
    #capture the first frame
    check,frame=video.read()
    frame = cv2.resize(frame, (600,400))
    gray=cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    detect = False

    #detect the faces from the video using detectMultiScale function
    faces=face_classifier.detectMultiScale(gray,1.3,5)
    eyes=eye_classifier.detectMultiScale(gray,1.3,5)

    print(faces)
    
    #drawing rectangle boundries for the detected face
    for(x,y,w,h) in faces:
        print(x,y,w,h)
        #print(type(x+h/2))
        detect = True
        cv2.circle(frame, (int(x+h/2),int(y+w/2)), int(w/2), (0,0,255), 2)
        cv2.imshow('Face detection', frame)
        picname=datetime.datetime.now().strftime("%y-%m-%d-%H-%M")
        cv2.imwrite(picname+".jpg",frame)
        multi_part_upload(bucket, picname+'.jpg', picname+'.jpg')
        json_document={"link":COS_ENDPOINT+'/'+bucket+'/'+picname+'.jpg'}
        response = service.post_document(db="access", document=json_document).get_result()
        print(response)
        
    #drawing rectangle boundries for the detected eyes
    for(ex,ey,ew,eh) in eyes:
        cv2.rectangle(frame, (ex,ey), (ex+ew,ey+eh), (0,0,255), 2)
        cv2.imshow('Face detection', frame)

    myData={'Face_detect': detect}
    client.publishEvent(eventId="status", msgFormat="json", data=myData, qos=0, onPublish=None)
    print("Data published to IBM IoT platfrom: ",myData)
    client.commandCallback = myCommandCallback
    time.sleep(2)
    #waitKey(1)- for every 1 millisecond new frame will be captured
    Key=cv2.waitKey(1)
    if Key==ord('q'):
        #release the camera
        video.release()
        #destroy all windows
        cv2.destroyAllWindows()
        break

