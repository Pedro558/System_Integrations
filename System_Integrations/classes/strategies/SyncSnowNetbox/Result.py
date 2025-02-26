import json

class Result():
    def __init__(self, new=[], update=[], delete=[], all=[]):
        self._new = new
        self._update = update
        self._delete = delete
        self.all = all


    def __str__(self):
        return json.dumps(self.all)


    @property
    def new(self) -> list:
        return self._new

    @new.setter
    def new(self, new: list) -> None:
        if not isinstance(new, list):
            new = [new]

        self._new = new
        self.all = [item for item in self.all if item not in self.new]
        self.all += new

    @property
    def update(self) -> list:
        return self._update

    @update.setter
    def update(self, update: list) -> None:
        if not isinstance(update, list):
            update = [update]

        self._update = update
        self.all = [item for item in self.all if item not in self.update]
        self.all += update

    @property
    def delete(self) -> list:
        return self._delete

    @delete.setter
    def delete(self, delete: list) -> None:
        if not isinstance(delete, list):
            delete = [delete]

        self._delete = delete
        self.all = [item for item in self.all if item not in self.delete]
        self.all += delete