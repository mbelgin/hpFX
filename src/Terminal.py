class Terminal:
    def __init__(self, name, path, exe, data_folder):
        self.name = name
        self.path = path
        self.exe = exe
        self.data_folder = data_folder

    def print(self):
        print("name         :    {}".format(self.name))
        print("path         :    {}".format(self.path))
        print("data_folder  :    {}".format(self.data_folder))
        print("exe          :    {}".format(self.exe))
        print()

    def run(self):
        pass



