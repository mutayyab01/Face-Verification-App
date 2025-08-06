class ContractorValidator:
    @staticmethod
    def validate_all(data):
        """Validate all contractor data"""
        errors = []
        
        if not data.get('name', '').strip():
            errors.append("Contractor name is required")
        
        if not data.get('father_name', '').strip():
            errors.append("Father name is required")
        
        return errors