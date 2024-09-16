from .base_dialog import BaseDialog

class IndexScoreDialog(BaseDialog):
    def __init__(self, on_accept_callback, parent=None):
        input_specs = {
            'title': 'Index Score Configuration',
            'elements': [
                {
                    'type': 'doublespinbox',
                    'label': 'Default Value',
                    'name': 'default_value',
                    'min': 0.0,
                    'max': 100.0,
                    'decimals': 2,
                    'default': 50.0
                },
                {
                    'type': 'spinbox',
                    'label': 'Allowed Range',
                    'name': 'allowed_range',
                    'min': 1,
                    'max': 10,
                    'default': 5
                },
                # other widgettes go here
            ]
        }
        super().__init__(input_specs, on_accept_callback, parent)
