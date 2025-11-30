"""Debug script to check revoke consent endpoint schema"""
import inspect
from app.schemas import consent as consent_schemas
from pydantic import BaseModel

print('=' * 60)
print('CONSENT SCHEMAS - Looking for Revoke')
print('=' * 60)

# Find all classes in consent schemas
for name in dir(consent_schemas):
    obj = getattr(consent_schemas, name)
    if inspect.isclass(obj) and issubclass(obj, BaseModel):
        if 'revoke' in name.lower():
            print(f'\n✓ Found: {name}')
            print(f'Fields: {obj.model_fields.keys()}')
            for field_name, field_info in obj.model_fields.items():
                print(f'  - {field_name}: {field_info.annotation}')

print('\n' + '=' * 60)
print('ALL CONSENT-RELATED SCHEMAS')
print('=' * 60)
for name in dir(consent_schemas):
    obj = getattr(consent_schemas, name)
    if inspect.isclass(obj) and issubclass(obj, BaseModel):
        print(f'- {name}')
