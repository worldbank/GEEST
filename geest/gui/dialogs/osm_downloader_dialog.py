from .base_dialog import BaseDialog

class OSMDownloaderDialog(BaseDialog):
    def __init__(self, on_accept_callback, parent=None):
        input_specs = {
            'title': 'OSM Downloader',
            'elements': [
                {
                    'type': 'radiobutton',
                    'label': 'Data Source',
                    'name': 'data_source',
                    'options': [
                        {'label': 'Manual Input', 'id': 'manual', 'checked': True},
                        {'label': 'Download from OSM', 'id': 'osm'}
                    ]
                },
                {
                    'type': 'lineedit',
                    'label': 'OSM Query',
                    'name': 'osm_query',
                    'default': 'highway=primary'
                },
                # more weedjits here
            ]
        }
        super().__init__(input_specs, on_accept_callback, parent)
