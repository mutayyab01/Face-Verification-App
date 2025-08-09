from werkzeug.utils import secure_filename
from datetime import datetime

class ContractorForm:
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

    @staticmethod
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ContractorForm.ALLOWED_EXTENSIONS

    @staticmethod
    def prepare_data(form_data, file_data):
        ContractorId = form_data.get('ContractorId')
        if ContractorId:
            try:
                ContractorId = int(ContractorId)
            except ValueError:
                ContractorId = None

        Name = form_data.get('Name', '').strip()
        FatherName = form_data.get('FatherName', '').strip()
        PhoneNumber = form_data.get('PhoneNumber', '').strip() 
        Unit = form_data.get('Unit', '').strip()
        Address = form_data.get('Address', '').strip()
        IsActive = 'IsActive' in form_data

        # Read image file as binary
        image_file = file_data.get('ProfileImage')
        image_binary = None
        if image_file and ContractorForm.allowed_file(image_file.filename):
            image_binary = image_file.read()  # read binary data

        return {
            'ContractorId': ContractorId,
            'Name': Name,
            'FatherName': FatherName,
            'PhoneNumber': PhoneNumber,
            'Unit': Unit,
            'ProfileImage': image_binary,
            'Address': Address,
            'IsActive': IsActive,
        }
