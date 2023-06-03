from PyQt5.QtCore import QSortFilterProxyModel, Qt, QThread
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIntValidator, QIcon
from PyQt5.QtWidgets import QHeaderView

from phoenixapi import phoenix
from time import sleep
import winsound
import psutil
from datetime import datetime
import json
from PyQt5 import QtCore, QtWidgets, uic


now = datetime.now()
current_time = now.strftime("[%H:%M:%S]")

def find_ports_by_process_name(process_name):
    ports = []
    connections = psutil.net_connections()
    for conn in connections:
        if conn.status == 'LISTEN':
            port = conn.laddr.port
            try:
                current_process = psutil.Process(conn.pid)
                if current_process.name() == process_name:
                    ports.append(f"{port}")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    return ports


def program():
    global stop
    stop = False
    port = port_box.currentText()
    if port != "None":
        window.label.setText(f"Selected Port: {port}")
        api = phoenix.Api(int(port))

        gold_limit_box = window.goldLimit
        validator = QIntValidator()
        gold_limit_box.setValidator(validator)
        # TIME
        now = datetime.now()
        current_time = now.strftime("[%H:%M:%S]")
        # TIMEEND
        try:
            gold_limit = int(gold_limit_box.text())
        except:
            log_box.append(f"{current_time} [ERROR] gold limit isn`t set correctly")
            exit()

        file = open('autoBuy.json')
        items_to_buy = json.load(file)
        last_sec = 0
        which_item_now = 0
        delay_time = int(window.delayTime.text())
        delay_time_route = int(window.delayTimeRoute.text())
        while api.working() and stop == False:
            # TIME
            now = datetime.now()
            current_time = now.strftime("[%H:%M:%S]")
            # TIMEEND
            if not api.empty():
                msg = api.get_message()
                json_msg = json.loads(msg)
                if json_msg["type"] == phoenix.Type.packet_recv.value and json_msg["packet"].startswith("rc_blist"):
                    first_ele = json_msg["packet"].split()[2].split("|")
                    for item in items_to_buy:
                        if first_ele[3] == item["id"]:
                            if window.advancedLogsBox.isChecked():
                                log_box.append(f"{current_time} [RECV] got information about {item['name']}")
                            if int(first_ele[6]) <= int(item["price_to_buy"]):
                                ilosc = int(first_ele[4])
                                while ilosc * int(first_ele[6]) > gold_limit:
                                    ilosc -= 1
                                    if ilosc == 0:
                                        if window.soundAllert.isChecked():
                                            winsound.Beep(2000, 500)
                                        log_box.append(
                                            f"{current_time} [NO GOLD] for {item['name']} in price: {first_ele[6]}")
                                    if ilosc * int(first_ele[6]) <= gold_limit:
                                        api.send_packet(
                                            f"c_buy {first_ele[0]} {first_ele[3]} {ilosc} {first_ele[6]}")
                                if int(first_ele[4]) * int(first_ele[6]) <= gold_limit:
                                    api.send_packet(f"c_buy {first_ele[0]} {first_ele[3]} {first_ele[4]} {first_ele[6]}")
                                    # PRINT
                            if item == items_to_buy[-1]:
                                if window.advancedLogsBox.isChecked():
                                    log_box.append(f"{current_time} [DELAY] {delay_time_route} sec")
                                sleep(delay_time_route)
                elif json_msg["type"] == phoenix.Type.packet_recv.value and json_msg["packet"].startswith("rc_buy"):
                    first_ele = json_msg["packet"].split()
                    if first_ele[1] != 0 and len(first_ele) >= 6:
                        if window.soundAllert.isChecked():
                            winsound.Beep(2000, 500)
                        for item in items_to_buy:
                            if item["id"] == str(first_ele[2]):
                                gold_limit -= int(first_ele[4])*int(first_ele[5])
                                log_box.append(f"{current_time} [PURCHASE] {item['name']} x{first_ele[4]} {first_ele[5]}/each")
                                log_box.append(f"Left {str(gold_limit)} gold")
            else:
                # TIME
                now = datetime.now()
                current_sec = now.strftime("%S")
                # TIMEEND
                if int(current_sec)%delay_time == 0 and last_sec != int(current_sec):
                    last_sec = int(current_sec)
                    if window.advancedLogsBox.isChecked():
                        log_box.append(f"{current_time} [SEND] packet to get information about {items_to_buy[which_item_now]['name']}")
                    api.send_packet(f"c_blist  0 0 0 0 0 0 0 0 1 {items_to_buy[which_item_now]['id']}")
                    which_item_now += 1
                    if which_item_now == len(items_to_buy):
                        which_item_now = 0
                    sleep(0.01)
        api.close()
        # TIME
        now = datetime.now()
        current_time = now.strftime("[%H:%M:%S]")
        # TIMEEND
        log_box.append(f"{current_time} [NOTIFY] api stop working")
        if window.soundAllert.isChecked():
            winsound.Beep(2000, 500)
        file.close()


if __name__ == "__main__":

    process_name = "NostaleClientX.exe"
    ports = find_ports_by_process_name(process_name)

    app = QtWidgets.QApplication([])
    window = uic.loadUi("untitled.ui")

    log_box = window.textEdit

    file = open("user_pref.json")
    user_pref = json.load(file)
    file.close()
    lang = user_pref["lang"]


    def change_lang():
        global lang
        if lang_box.currentText() != "Select Language: ":
            lang = lang_box.currentText()
            file = open("user_pref.json")
            user_pref = json.load(file)
            file.close()
            user_pref["lang"] = lang
            with open("user_pref.json", "w") as json_file:
                json.dump(user_pref, json_file)
            log_box.append(f"[UPDATE] language has been changed on {lang}")
            log_box.append(f"[IMPORTANT] if u changed language items names MUST be correct with your language")
            load_completer()
        else:
            log_box.append("[ERROR] select language")


    langs = ["Select Language: ", "cz", "de", "es", "fr", "it", "pl", "ru", "tr", "uk"]
    lang_box = window.langBox
    lang_box.addItems(langs)
    lang_box.setCurrentText(lang)
    lang_box.currentIndexChanged.connect(change_lang)

    port_box = window.portBox


    def find_port():
        global ports
        if ports:
            port_box.addItems(ports)
        else:
            port_box.addItem("None")


    find_port()

    file = open("items.json")
    items = json.load(file)
    file.close()
    model_sorter = QStandardItemModel()


    def load_completer():
        model_sorter.clear()
        for item in items:
            if lang != "Select Language: ":
                if item["flag"]["cannot_be_sold"] == False:
                    ele = QStandardItem(item["name"][lang])
                    model_sorter.appendRow(ele)
            else:
                log_box.append("[ERROR] select language")
                break


    load_completer()

    proxy_model = QSortFilterProxyModel()
    proxy_model.setSourceModel(model_sorter)


    item_name_box = window.itemNameBox
    completer = QtWidgets.QCompleter(proxy_model, item_name_box)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    item_name_box.setCompleter(completer)
    price_box = window.priceBox

    file = open('autoBuy.json')
    items_to_buy = json.load(file)
    file.close()


    def add_row():
        used_id = []
        for item in items_to_buy:
            used_id.append(item["id"])
        for item in items:
            if item["flag"]["cannot_be_sold"] == False and item["name"][lang] == item_name_box.currentText():
                if f"{item['id']}" not in used_id:
                    adden_dict = {"name": f"{item_name_box.currentText()}", "id": f"{item['id']}",
                                  "price_to_buy": f"{price_box.text()}"}
                    items_to_buy.append(adden_dict)
                    with open("autoBuy.json", "w") as json_file:
                        json.dump(items_to_buy, json_file)
                    show_autobuy()
                    log_box.append(
                        f"[ADD] {item['name'][lang]} has been added to autobuy for price(or lower): {price_box.text()}")
                    break
                else:
                    log_box.append(
                        f"[ERROR] {item['name'][lang]} is already in autoBuy, but meaby in other language")
                    break


    add_button = window.addButton
    add_button.clicked.connect(add_row)

    item_list = window.itemList
    model = QStandardItemModel()
    item_list.setModel(model)

    # This will make all columns stretch to fill the space
    item_list.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def show_autobuy():
        file = open('autoBuy.json')
        items_to_buy = json.load(file)
        file.close()
        model.clear()
        i = 0
        for item in items_to_buy:
            name_item = QStandardItem(f"{item['name']}")
            name_item.setEditable(False)
            #id_item = QStandardItem(f"{item['id']}")
            #id_item.setEditable(False)
            name_item.setEditable(False)
            model.appendRow([name_item, QStandardItem(f"{item['price_to_buy']}")])
            #model.appendRow([name_item, QStandardItem(f"{item['price_to_buy']}"), id_item])
        model.setHeaderData(0, QtCore.Qt.Horizontal, "Name")
        model.setHeaderData(1, QtCore.Qt.Horizontal, "Price to buy")
        #model.setHeaderData(2, QtCore.Qt.Horizontal, "Item id")


    show_autobuy()


    def remove_row():
        index = item_list.currentIndex()
        if index.isValid():
            item_name = index.sibling(index.row(), 0).data(Qt.DisplayRole)
            model.removeRow(index.row())
            for item in items_to_buy:
                if item['name'] == item_name:
                    items_to_buy.remove(item)
                    with open("autoBuy.json", "w") as json_file:
                        json.dump(items_to_buy, json_file)
                    log_box.append(f"[DELETE] {item_name} has been deleted from autoBuy")
                    break


    def handle_data_changed(index):
        if index.isValid():
            row = index.row()
            column = index.column()
            new_value = index.data(Qt.DisplayRole)
            item_name = model.index(row, column - 1).data(Qt.DisplayRole)
            for item in items_to_buy:
                if item['name'] == item_name:
                    item['price_to_buy'] = f"{new_value}"
                    with open("autoBuy.json", "w") as json_file:
                        json.dump(items_to_buy, json_file)
                    log_box.append(f"[UPDATE] price has been changed on {new_value} for {item_name}")
                    break


    # Podłączenie funkcji obsługującej do sygnału dataChanged
    model.dataChanged.connect(handle_data_changed)

    delete_button = window.deleteButton
    delete_button.clicked.connect(remove_row)


    class Worker(QThread):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.is_running = True

        def run(self):
            # TIME
            now = datetime.now()
            current_time = now.strftime("[%H:%M:%S]")
            # TIMEEND
            log_box.append(f"{current_time}[START] bot has been started")
            program()

        def stop(self):
            self.terminate()
            global stop
            stop = True
            # TIME
            now = datetime.now()
            current_time = now.strftime("[%H:%M:%S]")
            # TIMEEND
            log_box.append(f"{current_time}[STOP] bot has been stopped")


    worker = Worker()
    window.startButton.clicked.connect(worker.start)
    window.stopButton.clicked.connect(worker.stop)

    window.show()
    app.exec()
