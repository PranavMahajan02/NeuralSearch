from abc import ABC, abstractmethod


class BasePlatform(ABC):

    @abstractmethod
    def index(self):
        pass

    @abstractmethod
    def search(self, query):
        pass

    @abstractmethod
    def upload(self, file_path):
        pass

    @abstractmethod
    def delete(self, file_name):
        pass

    @abstractmethod
    def list_files(self):
        pass