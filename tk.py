from tkinter import *
from tkinter.ttk import *
import serial
import serial.tools.list_ports
import threading
from functools import partial
import time

'''
Set the gun frame
'''


class Gun(Frame):
    def __init__(self):
        super().__init__()

        self.ser = serial.Serial()
        # self.ser.baudrate = 38400
        # self.ser.parity = serial.PARITY_EVEN
        # self.ser.xonxoff = True
        # self.ser.bytesize = serial.EIGHTBITS

        self.ports_list = []

        '''
        Make the buttons be in place
        '''

        self.label = Label(self, text="Connection setup").grid(row=0, columnspan=2)

        self.ports_list_box = Combobox(self, value=self.ports_list, width=8)
        self.ports_list_box.grid(row=1, columnspan=2)

        self.connect_button = Button(self, text="Connect", command=self.connect)
        self.connect_button.grid(row=2, column=0)

        self.disconnect_button = Button(self, text="Disconnect", command=self.disconnect, state=NORMAL)
        self.disconnect_button.grid(row=2, column=1)

        self.connected_status = StringVar()
        self.connected_status.set('Disconnected\n')
        self.connected_status_label = Label(self, textvariable=self.connected_status).grid(row=4, columnspan=2)

        self.label = Label(self, text="\nMeasurement setup").grid(row=5, columnspan=2)
        self.number_of_measurements_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        self.label = Label(self, text='Number of meas.').grid(row=6, column=0)
        self.number_of_measurements_box = Combobox(self, value=self.number_of_measurements_list, width=4)
        self.number_of_measurements_box.grid(row=6, column=1)
        self.number_of_measurements_box.set(self.number_of_measurements_list[0])

        self.measure_button1 = Button(self,
                                      text="Measure\nS VA HA",
                                      command=partial(self.measure_in_thread, 'Measure S VA HA'),
                                      state=NORMAL,
                                      compound=CENTER)
        self.measure_button1.grid(row=8, column=0)

        self.measure_button2 = Button(self,
                                      text="Measure\nX Y Z",
                                      command=partial(self.measure_in_thread, 'Measure Coordinates'),
                                      state=NORMAL,
                                      compound=CENTER)
        self.measure_button2.grid(row=8, column=1)

        self.stop_button = Button(self, text="Stop", command=self.stop_measure).grid(row=10, columnspan=2)

        self.measurement_result_to_show = StringVar()
        self.measurement_result_to_show.set('No S VA HA results')
        self.measurement_result_to_show_label = Label(self, textvariable=self.measurement_result_to_show)
        self.measurement_result_to_show_label.grid(row=11, columnspan=2)

        self.measurement_coord_to_show = StringVar()
        self.measurement_coord_to_show.set('No X Y Z results')
        self.measurement_coord_to_show_label = Label(self, textvariable=self.measurement_coord_to_show)
        self.measurement_coord_to_show_label.grid(row=12, columnspan=2)

        self.label = Label(self, text="\nPointer setup").grid(row=13, columnspan=2)
        self.greet_button = Button(self, text="Pointer ON", command=self.pointer_on). \
            grid(row=14, column=0, sticky='ns')
        self.greet_button = Button(self, text="Pointer OFF", command=self.pointer_off). \
            grid(row=16, column=0, sticky='ns')
        self.greet_button = Button(self, text="Select laser\npointer", command=self.select_laser_pointer). \
            grid(row=14, column=1)
        self.greet_button = Button(self, text="Select guide\nlight", command=self.select_guide_light). \
            grid(row=16, column=1)

        self.label = Label(self, text="\nBacklight setup").grid(row=18, columnspan=2)
        self.greet_button = Button(self, text="Backlight ON", command=self.backlight_on).grid(row=19, column=0)
        self.greet_button = Button(self, text="Backlight OFF", command=self.backlight_off).grid(row=19, column=1)

        self.tracking_data_label = Label(self, text='\nTracking data').grid(row=20, columnspan=2)
        self.tracking_data_str = StringVar()
        self.tracking_data_str.set('Tracking data is disabled')
        self.tracking_data_status_label = Label(self, textvariable=self.tracking_data_str).grid(row=21, columnspan=2)
        self.tracking_data_on = Button(self, text='Start tracking', command=self.start_tracking_data_in_thread)
        self.tracking_data_on.grid(row=22, column=0)
        self.tracking_data_off = Button(self, text='Stop tracking', command=self.stop_tracking_data)
        self.tracking_data_off.grid(row=22, column=1)

        '''
        Set commands, boolean things and something to store data
        '''

        self.commands = {
            'Get ID': b'A\r\n',
            'Instrument station coordinates': b'Da\r\n',
            'Measure S VA HA': b'Ea\r\n',
            'Measure Coordinates': b'Ed\r\n',
            'VA HA Tilt': b'Ee\r\n',
            'Measure S VA HA X Y Z': b'Ei\r\n',
            'Stop measure': b'\x12\r\n',
            'Battery VA HA (tracking)': b'*ST1\r\n',
            'Battery S VA HA (tracking)': b'*ST3\r\n',
            'Stop battery VA HA (tracking)': b'*ST0\r\n',
            'Pointer ON': b'*GLON\r\n',
            'Pointer OFF': b'*GLOFF\r\n',
            'Select laser pointer': b'*/PF 2,1\r\n',
            'Select guide light': b'*/PF 1,1\r\n',
            'Backlight ON': b'Xs\r\n',
            'Backlight OFF': b'Xr\r\n',
            'Set measurement mode to Fine Repeat': b'Xb\r\n',
            'Set measurement mode to Fine Single': b'Xa\r\n'
        }

        self.instrument_id = None
        self.station_coordinates = None
        self.s_va_ha_results = []
        self.x_y_z_results = []
        self.va_ha_tilt = None
        self.s_va_ha_x_y_z = []
        self.tracking_status = False
        self.tracking_data_bool = False
        self.measuring = False
        self.connected = False
        self.laser_pointer = False
        self.guide_light = False
        self.last_result = []
        self.last_stored_result = {'X': 0.0,
                                   'Y': 0.0,
                                   'Z': 0.0}
        self.threads = []
        self.ports_thread = threading.Thread(target=self.get_ports_list)
        self.ports_thread.start()

    '''
    Set functions for the gun
    '''

    def output_str_to_list(self, output):
        output = output.decode('utf-8')
        output = output.rstrip('\r\n')
        output = output.split(' ', 1)
        try:
            output = [output[0]] + output[1].split(sep=',')
        except IndexError:
            output = 'bad line'
        if output != 'bad line':
            return output

    def send_command(self, command):
        while self.connected:
            self.ser.write(command)
            buffer = self.ser.readline()
            if buffer == b'\x06':
                print('Command executed successfully')
                return None
            if buffer == b'\x15':
                print('Error')
                return None
            if buffer is None:
                return None
            else:
                clean_buffer = self.output_str_to_list(buffer)
                if clean_buffer[0] == 'A':
                    self.instrument_id = clean_buffer
                if clean_buffer[0] == 'Da':
                    self.station_coordinates = clean_buffer
                if clean_buffer[0] == 'Ea':
                    self.last_result = clean_buffer

    def get_ports_list(self):
        ports_list = []
        sse = serial.tools.list_ports.comports()
        for item in sse:
            ports_list.append(item.device)
        self.ports_list = sorted(ports_list)
        self.ports_list_box['values'] = self.ports_list
        print('Ports scanned')

    def connect(self):
        self.ser.port = self.ports_list_box.get()
        self.ser.timeout = 0.25
        self.ser.open()
        connected = self.ser.is_open
        if connected:
            self.connected = True
        if self.connected:
            self.ser.write(self.commands.get('Get ID'))
            time.sleep(2)
            self.instrument_id = self.output_str_to_list(self.ser.readline())
            print('Connected to {} {}'.format(self.instrument_id[1], self.instrument_id[2]))
            self.ser.write(self.commands.get('Set measurement mode to Fine Single'))
            self.connected_status.set('Connected to \n{} {}'.format(self.instrument_id[1], self.instrument_id[2]))
            # self.tracking_angles_in_thread()

    def disconnect(self):
        if self.connected:
            # self.stop_tracking_angles()
            self.ser.close()
            self.connected = False
            print('Disconnected')
            self.connected_status.set('Disconnected\n')

    # def edm_measure_result(self):
    #     measurement_result = self.ser.readline()
    #     if measurement_result != b'':
    #         range_result = measurement_result[:7].decode('utf-8')
    #         va_result = measurement_result[8:15].decode('utf-8')
    #         ha_result = measurement_result[16:23].decode('utf-8')
    #         measurement_result_to_show = 'measured'
    #         print(measurement_result_to_show)
    #         self.last_result = [range_result, va_result, ha_result]
    #         return measurement_result_to_show
    #     if measurement_result is None:
    #         pass

    # def measure_result(self):
    #     measurement_result = self.ser.readline()
    #     print(measurement_result)
    #     measurement_result = measurement_result.decode('utf-8')
    #     measurement_result = measurement_result.rstrip('\r\n')
    #     measurement_result = measurement_result.split(sep=',')
    #     x_result = measurement_result[5]
    #     y_result = measurement_result[6]
    #     z_result = measurement_result[7]
    #     self.last_stored_result = {'X': x_result,
    #                                'Y': y_result,
    #                                'Z': z_result}
    #     measurement_result_to_show = 'X={X}, Y={Y}, Z={Z}'.format(**self.last_stored_result)
    #     print(measurement_result_to_show)
    #     return measurement_result_to_show

    def measure(self, command):
        if self.tracking_status is True:
            self.stop_tracking_angles()
            self.ser.readlines()
        if self.tracking_status is False:
            self.ser.readlines()
            self.measuring = True
            print(str(int(self.number_of_measurements_box.get())) + ' measurements set')
            if int(self.number_of_measurements_box.get()) == 1:
                self.ser.write(self.commands.get('Set measurement mode to Fine Single'))
            else:
                self.ser.write(self.commands.get('Set measurement mode to Fine Repeat'))
            with self.measure_thread_lock:
                print('readlines in measure')
                self.ser.readlines()
                self.ser.write(self.commands.get(command))
                number_of_measurements_done = 0
                while self.measuring:
                    measurement_result = self.ser.readline()
                    if measurement_result is not None:
                        if measurement_result == b'\x15':
                            print('Error')
                            self.ser.write(self.commands.get('Stop'))
                            print('Aborted')
                            break
                        if measurement_result != b'' and measurement_result != b'\x06':
                            number_of_measurements_done += 1
                            print(number_of_measurements_done, ' measurements done')
                            measurement_result = self.output_str_to_list(measurement_result)
                            print(measurement_result)
                            x_result = measurement_result[5]
                            y_result = measurement_result[6]
                            z_result = measurement_result[7]
                            self.last_stored_result = {'X': x_result,
                                                       'Y': y_result,
                                                       'Z': z_result}
                            self.measurement_coord_to_show.set('X={X}, Y={Y}, Z={Z}'.format(**self.last_stored_result))
                    if number_of_measurements_done == int(self.number_of_measurements_box.get()):
                        self.stop_measure()
                        self.tracking_status = True
                        # self.tracking_angles_in_thread()
                        break
                    if not self.measuring:
                        break
            self.measure_button1.configure(state=NORMAL)
            self.measure_button2.configure(state=NORMAL)

    def measure_in_thread(self, command):
        self.measuring = False
        self.measure_button1.configure(state=DISABLED)
        self.measure_button2.configure(state=DISABLED)
        print(command)
        self.measure_thread = threading.Thread(target=self.measure, args=(command,))
        self.measure_thread_lock = threading.Lock()
        self.measure_thread.start()

    def stop_measure(self):
        self.ser.write(self.commands.get('Stop measure'))
        self.measuring = False
        self.measure_button1.configure(state=NORMAL)
        self.measure_button2.configure(state=NORMAL)

    def tracking_angles(self):
        while self.tracking_status:
            if not self.measuring:
                print('VA HA Tilt send')
                self.ser.write(self.commands.get('VA HA Tilt'))
                time.sleep(0.2)
                result = self.ser.readline()
                print('VA HA Tilt received')
                if result is not None:
                    if result != b'':
                        print(result)
                        self.measurement_result_to_show.set(result)

    def stop_tracking_angles(self):
        # self.ser.write(self.commands.get('Stop battery VA HA (tracking)'))
        self.ser.readline()
        self.tracking_status = False

    def tracking_angles_in_thread(self):
        self.tracking_status = True
        # self.ser.write(self.commands.get('Battery VA HA (tracking)'))
        self.tracking_thread = threading.Thread(target=self.tracking_angles)
        self.tracking_thread.start()

    def pointer_on(self):
        self.ser.write(self.commands.get('Pointer ON'))
        print(self.ser.readline())

    def pointer_off(self):
        self.ser.write(self.commands.get('Pointer OFF'))
        print(self.ser.readline())

    def select_laser_pointer(self):
        self.ser.write(self.commands.get('Select laser pointer'))
        print(self.ser.readline())

    def select_guide_light(self):
        self.ser.write(self.commands.get('Select guide light'))
        print(self.ser.readline())

    def backlight_on(self):
        self.ser.write(self.commands.get('Backlight ON'))
        print(self.ser.readline())

    def backlight_off(self):
        self.ser.write(self.commands.get('Backlight OFF'))
        print(self.ser.readline())

    def tracking_data_processor(self):
        while self.tracking_data_bool is True:
            data = self.ser.readline()
            time.sleep(0.2)
            if data == b'\x15':
                print('Error')
                break
            if data != b'' and data != b'\x06' and data is not None:
                measurement_result = self.output_str_to_list(data)
                print(measurement_result)
                if measurement_result[5] != 'E115' and measurement_result[5] != 'E200':
                    x_result = measurement_result[5]
                    y_result = measurement_result[6]
                    z_result = measurement_result[7]
                    self.last_stored_result = {'X': x_result,
                                               'Y': y_result,
                                               'Z': z_result}
                    self.measurement_coord_to_show.set('X={X}m, Y={Y}m, Z={Z}m'.format(**self.last_stored_result))
            else:
                continue

    def start_tracking_data(self):
        self.tracking_data_bool = True
        self.tracking_data_str.set('Tracking data')
        self.tracking_data_processor()

    def start_tracking_data_in_thread(self):
        self.tracking_data_in_thread = threading.Thread(target=self.start_tracking_data)
        self.tracking_data_in_thread.start()

    def stop_tracking_data(self):
        self.tracking_data_bool = False
        self.tracking_data_str.set('Tracking data is disabled')


'''
Set calculate window
'''


class CalculateFrame(Frame):
    def __init__(self):
        super().__init__()
        self.delta_x = float(0)
        self.delta_y = float(0)
        self.delta_z = float(0)
        self.delta_x_coeff = DoubleVar()
        self.delta_x_coeff.set(1.0)
        self.delta_y_coeff = DoubleVar()
        self.delta_y_coeff.set(1.0)
        self.delta_z_coeff = DoubleVar()
        self.delta_z_coeff.set(1.0)

        self.label = Label(self, text='Delta results').grid(row=0, columnspan=6)
        self.calculate_delta_button = Button(self, text="Calculate",
                                             command=lambda: self.calculate_delta(app.gun1, app.gun2))
        self.calculate_delta_button.grid(row=1, columnspan=6)
        self.delta_results = StringVar()
        self.delta_results.set('No delta')
        self.label = Label(self, textvariable=self.delta_results).grid(row=2, columnspan=6)
        self.label = Label(self, text='\nDelta results with correction').grid(row=3, columnspan=6)
        self.delta_x_coeff_label = Label(self, text=' kX =').grid(row=4, column=0)
        self.delta_x_coeff_entry = Entry(self, textvariable=self.delta_x_coeff, width=4)
        self.delta_x_coeff_entry.grid(row=4, column=1)
        self.delta_y_coeff_label = Label(self, text=' kY =').grid(row=4, column=2)
        self.delta_y_coeff_entry = Entry(self, textvariable=self.delta_y_coeff, width=4)
        self.delta_y_coeff_entry.grid(row=4, column=3)
        self.delta_z_coeff_label = Label(self, text=' kZ =').grid(row=4, column=4)
        self.delta_z_coeff_entry = Entry(self, textvariable=self.delta_z_coeff, width=4)
        self.delta_z_coeff_entry.grid(row=4, column=5)

        self.close_button = Button(self, text="Close", command=self.quit).grid(row=5, column=0, columnspan=6, sticky=S)

    def calculate_delta(self, object1, object2):
        delta_x = self.delta_x_coeff.get() * (
                float(object2.last_stored_result.get('X')) - float(object1.last_stored_result.get('X')))
        delta_y = self.delta_y_coeff.get() * (
                float(object2.last_stored_result.get('Y')) - float(object1.last_stored_result.get('Y')))
        delta_z = self.delta_z_coeff.get() * (
                float(object2.last_stored_result.get('Z')) - float(object1.last_stored_result.get('Z')))
        delta = {'dX': delta_x,
                 'dY': delta_y,
                 'dZ': delta_z}
        delta_to_set = 'dX={}mm \ndY={}mm \ndZ={}mm'.format(
            round(delta.get('dX')*1000, 3),
            round(delta.get('dY')*1000, 3),
            round(delta.get('dZ')*1000, 3))
        self.delta_results.set(delta_to_set)
        return delta_to_set

    # def output_str_to_list(self, output):
    #     output = output.decode('utf-8')
    #     output = output.rstrip('\r\n')
    #     output = output.split(' ', 1)
    #     try:
    #         output = [output[0]] + output[1].split(sep=',')
    #     except IndexError:
    #         output = 'bad line'
    #     if output != 'bad line':
    #         return output
    #
    # def tracking_data_processor(self, gun):
    #     while self.tracking_data_status is True:
    #         data = gun.ser.readline()
    #         print(gun.instrument_id)
    #         if data == b'\x15':
    #             print('Error')
    #             break
    #         if data != b'' and data != b'\x06' and data is not None:
    #             measurement_result = self.output_str_to_list(data)
    #             print(measurement_result)
    #             x_result = measurement_result[5]
    #             y_result = measurement_result[6]
    #             z_result = measurement_result[7]
    #             gun.last_stored_result = {'X': x_result,
    #                                       'Y': y_result,
    #                                       'Z': z_result}
    #             gun.measurement_coord_to_show.set('X={X}, Y={Y}, Z={Z}'.format(**gun.last_stored_result))
    #
    # def start_tracking_data(self):
    #     self.tracking_data_status = True
    #     self.tracking_data.set('Tracking data')
    #     self.tracking_data_processor(app.gun1)
    #     self.tracking_data_processor(app.gun2)
    #
    # def start_tracking_data_in_thread(self):
    #     self.tracking_data_in_thread = threading.Thread(target=self.start_tracking_data)
    #     self.tracking_data_in_thread.start()
    #
    # def stop_tracking_data(self):
    #     self.tracking_data_status = False
    #     self.tracking_data_label.set('Tracking data is disabled')


'''
Set big window with results of measurements and auto calculation of deviations
'''


class BigResultsWindow(Toplevel):
    def __init__(self):
        super().__init__()
        self.title = 'Big results window'

        self.gun1_text = StringVar()
        self.gun1_text.set('X={}\n'
                           'Y={}\n'
                           'Z={}'.format((self.show_coord_gun(app.gun1).get('X')),
                                         (self.show_coord_gun(app.gun1).get('Y')),
                                         (self.show_coord_gun(app.gun1).get('Z'))))
        self.gun2_text = StringVar()
        self.gun2_text.set('X={}\n'
                           'Y={}\n'
                           'Z={}'.format((self.show_coord_gun(app.gun2).get('X')),
                                         (self.show_coord_gun(app.gun2).get('Y')),
                                         (self.show_coord_gun(app.gun2).get('Z'))))

        self.calc_text = StringVar()
        self.calculate_delta_b = True
        self.calc_text.set(self.show_delta_in_thread())  # It must be dynamically changing text
        self.show_delta_thread_running = True

        self.label_gun1 = Label(self, textvariable=self.gun1_text)
        self.label_gun1.config(font=("Courier", 100))
        self.label_gun1.grid(row=0, column=0, sticky=NW)
        self.columnconfigure(1, weight=1)

        self.label_gun2 = Label(self, textvariable=self.gun2_text)
        self.label_gun2.config(font=("Courier", 100))
        self.label_gun2.grid(row=0, column=1, sticky=NE)

        self.separator = Separator(self, orient=HORIZONTAL)
        self.separator.grid(row=1, columnspan=2, sticky=(N, W))

        self.label_calc = Label(self, textvariable=self.calc_text)
        self.label_calc.config(font=("Courier", 100))
        self.label_calc.grid(row=2, columnspan=2)

        self.delta_x_coeff = app.calc1.delta_x_coeff.get()
        self.delta_y_coeff = app.calc1.delta_y_coeff.get()
        self.delta_z_coeff = app.calc1.delta_z_coeff.get()

        self.protocol('WM_DELETE_WINDOW', lambda: self.closeEvent())

    def show_coord_gun(self, gun):
        x = lambda: gun.last_stored_result.get('X')
        y = lambda: gun.last_stored_result.get('Y')
        z = lambda: gun.last_stored_result.get('Z')
        gun_last_result = {'X': x(),
                           'Y': y(),
                           'Z': z()}
        return gun_last_result

    def show_delta(self):
        while self.calculate_delta_b:
            delta = CalculateFrame.calculate_delta(app.calc1, app.gun1, app.gun2)
            self.calc_text.set(delta)
            time.sleep(2)
            if self.show_delta_in_thread is False:
                break

    def show_delta_in_thread(self):
        self.thread1 = threading.Thread(target=self.show_delta)
        self.thread1.start()

    def closeEvent(self):
        self.show_delta_in_thread = False
        self.destroy()

class MainApplication(Tk):
    def __init__(self):
        super().__init__()
        self.title('RUKI BAZUKI')

        '''
        Start of menu
        '''

        self.menu_bar = Menu(self)
        self.edit_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label='Edit', menu=self.edit_menu)
        self.edit_menu.add_cascade(label='Big results window', command=self.open_big_results_window)
        self.config(menu=self.menu_bar)

        '''
        End of menu
        '''

        self.gun1 = Gun()
        self.gun2 = Gun()
        self.calc1 = CalculateFrame()
        self.gun1.grid(row=1, column=0, sticky=NW)
        self.calc1.grid(row=1, column=1, sticky=N, pady=20, padx=10)
        self.gun2.grid(row=1, column=2, sticky=NE)
        self.columnconfigure(1, weight=2)

    def open_big_results_window(self):
        BigResultsWindow()


app = MainApplication()
# app.geometry('700x700')  # wide x height
app.resizable(width=True, height=False)

app.mainloop()
