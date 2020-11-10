from typing import List

from webilastik.ui.applet import Applet, ValueSlot, CONFIRMER
from ndstructs.datasource import DataSource

class DataSelectionApplet(Applet):
    def __init__(self):
        self.datasources = ValueSlot[List[DataSource]](owner=self)
        super().__init__()

    def add_datasources(self, datasources: List[DataSource], confirmer: CONFIRMER) -> None:
        current_datasources: List[DataSource] = self.datasources() or []
        for ds in datasources:
            if ds in current_datasources:
                raise ValueError(f"Datasource {ds} has already been added")
        self.datasources.set_value(current_datasources + datasources, confirmer=confirmer)

    def remove_datasource(self, datasource_idx: int, confirmer: CONFIRMER) -> None:
        datasources: List[DataSource] = self.datasources() or []
        if datasource_idx >= len(datasources):
            raise ValueError(f"There is no datasource at index {datasource_idx}")
        del datasources[datasource_idx]
        self.datasources.set_value(datasources, confirmer=confirmer)
