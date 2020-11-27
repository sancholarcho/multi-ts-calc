from tkinter import *
from tkinter.ttk import *
from serial import Serial
import serial.tools.list_ports
import threading


class Gun(Frame):
    def __init__(self):
        super().__init__()
        self.label = Label(self, text="Connection setup").grid(row=0, column=0)

        self.ports_list = []
        self.get_ports_list()
        self.ports_list_box = Combobox(self, value=self.ports_list, width=8)
        self.ports_list_box.grid(row=1, column=0)

        self.connect_button = Button(self, text="Connect", command=self.connect)
        self.connect_button.grid(row=2, column=0)

        self.disconnect_button = Button(self, text="Disconnect", command=self.disconnect)
        self.disconnect_button.grid(row=3, column=0)

        self.connected_status = StringVar()
        self.connected_status.set('Disconnected')
        self.connected_status_label = Label(self, textvariable=self.connected_status).grid(row=4, column=0)

        self.label = Label(self, text="\nMeasurement setup").grid(row=6, column=0)
        self.measure_button = Button(self, text="Measure S VA HA", command=self.measure_raw_in_thread).\
            grid(row=7, column=0)
        self.measure_button = Button(self, text="Measure X Y Z", command=self.measure_coord_in_thread).\
            grid(row=8, column=0)
        self.stop_button = Button(self, text="Stop", command=self.stop_measure).grid(row=9, column=0)
        self.stop_button = Button(self, text="Read All", command=self.read_all_lines).grid(row=10, column=0)
        self.measurement_result_to_show = StringVar()
        self.measurement_result_to_show.set('No results')
        self.measurement_result_to_show_label = Label(self, textvariable=self.measurement_result_to_show)
        self.measurement_result_to_show_label.grid(row=11, column=0)

        self.measurement_coord_to_show = StringVar()
        self.measurement_coord_to_show.set('No results')
        self.measurement_coord_to_show_label = Label(self, textvariable=self.measurement_coord_to_show)
        self.measurement_coord_to_show_label.grid(row=12, column=0)

        self.label = Label(self, text="\nPointer setup").grid(row=13, column=0)
        self.greet_button = Button(self, text="Pointer ON", command=self.pointer_on).\
            grid(row=14, column=0)
        self.greet_button = Button(self, text="Pointer OFF", command=self.pointer_off).\
            grid(row=15, column=0)
        self.greet_button = Button(self, text="Select laser pointer", command=self.select_laser_pointer).\
            grid(row=16, column=0)
        self.greet_button = Button(self, text="Select guide light", command=self.select_guide_light).\
            grid(row=17, column=0)

        self.label = Label(self, text="\nBacklight setup").grid(row=18, column=0)
        self.greet_button = Button(self, text="Backlight ON", command=self.backlight_on).grid(row=19, column=0)
        self.greet_button = Button(self, text="Backlight OFF", command=self.backlight_off).grid(row=20, column=0)

        self.close_button = Button(self, text="Close", command=self.quit).grid(row=21, column=0)

        self.measuring = False
        self.connected = False
        self.laser_pointer = False
        self.guide_light = False
        self.last_result = []
        self.last_stored_result = {'X': 0.0,
                                   'Y': 0.0,
                                   'Z': 0.0}
        self.ser = Serial()

    def get_ports_list(self):
        ports_list = []
        sse = serial.tools.list_ports.comports()
        for item in sse:
            ports_list.append(item.device)
        self.ports_list = sorted(ports_list)

    def connect(self):
        self.ser.port = self.ports_list_box.get()
        self.ser.timeout = 0.1
        self.ser.open()
        output = self.ser.readline()
        if output == b'':
            self.connected = True
        if self.connected:
            print('Connected')
            self.connected_status.set('Connected')

    def disconnect(self):
        self.ser.close()
        self.connected = False
        print('Disconnected')
        self.connected_status.set('Disconnected')

    def edm_measure_result(self):
        measurement_result = self.ser.readline()
        if measurement_result != b'':
            range_result = measurement_result[:7].decode('utf-8')
            va_result = measurement_result[8:15].decode('utf-8')
            ha_result = measurement_result[16:23].decode('utf-8')
            # measurement_result_to_show = ('S=' + range_result[:4] + '.' + range_result[4:] + ' '
            #                                                                                  "VA=" + va_result[
            #                                                                                          :3] + "°" + va_result[
            #                                                                                                      3:5] + "'" + va_result[
            #                                                                                                                   5:] + '"' + ' '
            #                                                                                                                               "HA=" + ha_result[
            #                                                                                                                                       :3] + "°" + ha_result[
            #                                                                                                                                                   3:5] + "'" + ha_result[
            #                                                                                                                                                                5:] + '"')
            measurement_result_to_show = 'measured'
            print(measurement_result_to_show)
            self.last_result = [range_result, va_result, ha_result]
            return measurement_result_to_show
        if measurement_result is None:
            pass

    def coord_measure_result(self):
        measurement_result = self.ser.readline()
        if measurement_result != b'':
            measurement_result = measurement_result.decode('utf-8')
            measurement_result = measurement_result.rstrip('\r\n')
            measurement_result = measurement_result.split(sep=',')
            x_result = measurement_result[4]
            y_result = measurement_result[5]
            z_result = measurement_result[6]
            self.last_stored_result = {'X': x_result,
                                       'Y': y_result,
                                       'Z':  z_result}
            measurement_result_to_show = 'X={X}, Y={Y}, Z={Z}'.format(**self.last_stored_result)
            print(measurement_result_to_show)
            return measurement_result_to_show
        if measurement_result is None:
            pass

    def measure_raw(self):
        self.measuring = True
        self.ser.readline()
        self.ser.write(b'Ea\r\n')
        while self.measuring:
            edm_measure_result = self.edm_measure_result()
            if edm_measure_result != None:
                self.measurement_result_to_show.set(edm_measure_result)
            if not self.measuring:
                break

    def measure_coord(self):
        self.measuring = True
        self.ser.readline()
        self.ser.write(b'Ed\r\n')
        while self.measuring:
            measure_result = self.coord_measure_result()
            if measure_result is not None:
                self.measurement_coord_to_show.set(measure_result)

            if not self.measuring:
                break

    def measure_raw_in_thread(self):
        self.thread = threading.Thread(target=self.measure_raw)
        self.thread.start()

    def measure_coord_in_thread(self):
        self.thread = threading.Thread(target=self.measure_coord)
        self.thread.start()

    def stop_measure(self):
        self.ser.write(b'\x12\r\n')
        self.measuring = False
        self.edm_measure_result()

    def pointer_on(self):
        self.ser.write(b'*GLON\r\n')
        print(self.ser.readline())

    def pointer_off(self):
        self.ser.write(b'*GLOFF\r\n')
        print(self.ser.readline())

    def select_laser_pointer(self):
        self.ser.write(b'*/PF 2,1\r\n')
        print(self.ser.readline())

    def select_guide_light(self):
        self.ser.write(b'*/PF 1,1\r\n')
        print(self.ser.readline())

    def backlight_on(self):
        self.ser.write(b'Xs\r\n')
        print(self.ser.readline())

    def backlight_off(self):
        self.ser.write(b'Xr\r\n')
        print(self.ser.readline())

    def read_all_lines(self):
        lines = self.ser.readline()
        if lines != b'':
            return print(lines)
        else:
            print('No data to read')


class CalculateFrame(Frame):
    def __init__(self):
        super().__init__()
        self.delta_x = float(0)
        self.delta_y = float(0)
        self.delta_z = float(0)
        self.label = Label(self, textvariable='Delta results').grid(row=0, column=0)
        self.calculate_delta_button = Button(self, text="Calculate",
                                             command=lambda: self.calculate_delta(app.gun1, app.gun2))
        self.calculate_delta_button.grid(row=1, column=0)
        self.delta_results = StringVar()
        self.delta_results.set('No delta')
        self.delta_results_label = Label(self, textvariable=self.delta_results).grid(row=2, column=0)

    def calculate_delta(self, object1, object2):
        delta_x = float(object2.last_stored_result.get('X'))-float(object1.last_stored_result.get('X'))
        delta_y = float(object2.last_stored_result.get('Y'))-float(object1.last_stored_result.get('Y'))
        delta_z = float(object2.last_stored_result.get('Z'))-float(object1.last_stored_result.get('Z'))
        delta = {'dX': delta_x,
                 'dY': delta_y,
                 'dZ': delta_z}
        self.delta_results.set(
            'dX={}, dY={}, dZ={}'.format(
                round(delta.get('dX'), 3),
                round(delta.get('dY'), 3),
                round(delta.get('dZ'), 3)))
        return print('dX={}, dY={}, dZ={}'.format(
                round(delta.get('dX'), 3),
                round(delta.get('dY'), 3),
                round(delta.get('dZ'), 3)))


class MainApplication(Tk):
    def __init__(self):
        super().__init__()
        self.title('RUKI BAZUKI')
        self.gun1 = Gun()
        self.gun2 = Gun()
        self.calc1 = CalculateFrame()
        self.gun1.grid(row=0, column=0, sticky=NW)
        self.calc1.grid(row=0, column=1, sticky=N)
        self.gun2.grid(row=0, column=2, sticky=NE)


app = MainApplication()
app.geometry('500x500')
app.resizable(width=True, height=False)
app.columnconfigure(1, weight=2)

app.mainloop()
