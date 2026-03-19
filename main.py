import wx
import requests
import xml.etree.ElementTree as ET
import threading

class SolarApp(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title='Монитор солнечной активности R1BQE', size=(450, 500))
        self.panel = wx.Panel(self)
        
        # Основной контейнер
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Создаем notebook для вкладок
        self.notebook = wx.Notebook(self.panel)
        
        # Первая вкладка: Индексы солнечной активности
        self.indexes_panel = wx.Panel(self.notebook)
        self.indexes_sizer = wx.BoxSizer(wx.VERTICAL)
        self.list_ctrl = wx.ListCtrl(self.indexes_panel, style=wx.LC_REPORT | wx.BORDER_SUNKEN)
        self.list_ctrl.InsertColumn(0, 'Параметр', width=150)
        self.list_ctrl.InsertColumn(1, 'Значение', width=150)
        self.list_ctrl.InsertColumn(2, 'Описание', width=200)
        self.indexes_sizer.Add(self.list_ctrl, 1, wx.ALL | wx.EXPAND, 10)
        self.indexes_panel.SetSizer(self.indexes_sizer)
        self.notebook.AddPage(self.indexes_panel, 'Индексы солнечной активности')
        
        # Вторая вкладка: КВ Диапазоны
        self.bands_panel = wx.Panel(self.notebook)
        self.bands_sizer = wx.BoxSizer(wx.VERTICAL)
        self.bands_list = wx.ListCtrl(self.bands_panel, style=wx.LC_REPORT | wx.BORDER_SUNKEN)
        self.bands_list.InsertColumn(0, 'Диапазон', width=100)
        self.bands_list.InsertColumn(1, 'Днём', width=100)
        self.bands_list.InsertColumn(2, 'Ночью', width=100)
        self.bands_sizer.Add(self.bands_list, 1, wx.ALL | wx.EXPAND, 10)
        self.bands_panel.SetSizer(self.bands_sizer)
        self.notebook.AddPage(self.bands_panel, 'КВ Диапазоны')
        
        # Третья вкладка: УКВ Условия
        self.vhf_panel = wx.Panel(self.notebook)
        self.vhf_sizer = wx.BoxSizer(wx.VERTICAL)
        self.vhf_list = wx.ListCtrl(self.vhf_panel, style=wx.LC_REPORT | wx.BORDER_SUNKEN)
        self.vhf_list.InsertColumn(0, 'Феномен', width=200)
        self.vhf_list.InsertColumn(1, 'Значение', width=150)
        self.vhf_sizer.Add(self.vhf_list, 1, wx.ALL | wx.EXPAND, 10)
        self.vhf_panel.SetSizer(self.vhf_sizer)
        self.notebook.AddPage(self.vhf_panel, 'УКВ Условия')
        
        # Кнопка обновления
        self.refresh_btn = wx.Button(self.panel, label='Обновить данные (F5)')
        self.refresh_btn.Bind(wx.EVT_BUTTON, self.on_refresh)
        
        # Горячие клавиши
        accel_tbl = wx.AcceleratorTable([
            (wx.ACCEL_NORMAL, wx.WXK_F5, self.refresh_btn.GetId())
        ])
        self.SetAcceleratorTable(accel_tbl)
        
        self.sizer.Add(self.notebook, 1, wx.ALL | wx.EXPAND, 10)
        self.sizer.Add(self.refresh_btn, 0, wx.ALL | wx.CENTER, 10)
        
        self.panel.SetSizer(self.sizer)
        
        # Автозагрузка при старте
        self.on_refresh(None)
        self.Show()

    def get_k_desc(self, k):
        try:
            k = int(k)
            if k <= 1: return "Очень спокойно"
            if k <= 3: return "Спокойно"
            if k == 4: return "Нестабильно"
            return "Магнитная буря!"
        except:
            return ""

    def translate_condition(self, cond):
        trans = {
            'Poor': 'Плохо',
            'Fair': 'Средне',
            'Good': 'Хорошо',
            'Excellent': 'Отлично',
            'Band Closed': 'Закрыт',
            'Band Open': 'Открыт'
        }
        return trans.get(cond, cond)

    def translate_vhf_name(self, name):
        trans = {
            'vhf-aurora': 'Аврора (отражение от полярного сияния)',
            'E-Skip': 'Спорадическое прохождение (E-слой)'
        }
        return trans.get(name, name)

    def translate_vhf_loc(self, loc):
        trans = {
            'northern_hemi': 'Северное полушарие',
            'europe': 'Европа',
            'north_america': 'Северная Америка',
            'europe_6m': 'Европа 50 МГц (6м)',
            'europe_4m': 'Европа 70 МГц (4м)'
        }
        return trans.get(loc, loc)

    def load_data(self, is_manual):
        url = 'https://www.hamqsl.com/solarxml.php'
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            data = root.find('solardata')
            
            # Словарь параметров для вывода
            params = [
                ('SFI (Поток)', data.findtext('solarflux'), 'Индекс солнечного потока. Показывает ионизацию. Выше 150 — отлично для 10-15м, ниже 70 — ВЧ диапазоны закрыты.'),
                ('Sunspots (Пятна)', data.findtext('sunspots'), 'Число солнечных пятен. Чем больше пятен, тем лучше ионизация и выше частоты прохождения.'),
                ('A-Index', data.findtext('aindex'), 'Индекс геомагнитной активности. Низкие значения (0-7) — спокойные условия, высокие — бури.'),
                ('K-Index', f"{data.findtext('kindex')} ({self.get_k_desc(data.findtext('kindex'))})", 'Индекс геомагнитной активности по шкале K. 0-9, где 0 — очень спокойно, 5+ — буря.'),
                ('Magnetic Field', data.findtext('magfield'), 'Магнитное поле Земли в нТ. Нормально 20-40 нТ.'),
                ('Solar Wind', f"{data.findtext('solarwind')} км/с", 'Скорость солнечного ветра. Выше 500 км/с — возможны бури.'),
                ('MUF', data.findtext('muf'), 'Максимальная usable frequency — максимальная частота для прохождения.'),
                ('Signal Noise', data.findtext('signalnoise'), 'Шум сигнала. Высокий шум ухудшает связь.'),
            ]
            
            # КВ Диапазоны
            bands_data = {}
            calculatedconditions = data.find('calculatedconditions')
            if calculatedconditions is not None:
                for band in calculatedconditions.findall('band'):
                    name = band.get('name')
                    time = band.get('time')
                    condition = band.text
                    if name not in bands_data:
                        bands_data[name] = {'day': '—', 'night': '—'}
                    if condition:
                        bands_data[name][time] = self.translate_condition(condition.strip())
            
            # УКВ Условия
            vhf_data = []
            calculatedvhf = data.find('calculatedvhfconditions')
            if calculatedvhf is not None:
                for phen in calculatedvhf.findall('phenomenon'):
                    name = phen.get('name')
                    location = phen.get('location')
                    val = phen.text
                    if val:
                        translated_name = self.translate_vhf_name(name)
                        translated_loc = self.translate_vhf_loc(location)
                        translated_val = self.translate_condition(val.strip())
                        vhf_data.append((f"{translated_name} ({translated_loc})", translated_val))
            
            wx.CallAfter(self.update_list, params, bands_data, vhf_data, is_manual)
                
        except Exception as e:
            wx.CallAfter(self.show_error, str(e))

    def update_list(self, params, bands_data, vhf_data, is_manual):
        self.list_ctrl.DeleteAllItems()
        for i, (label, value, desc) in enumerate(params):
            self.list_ctrl.InsertItem(i, label)
            self.list_ctrl.SetItem(i, 1, str(value))
            self.list_ctrl.SetItem(i, 2, desc)
        
        self.bands_list.DeleteAllItems()
        for i, (band, times) in enumerate(bands_data.items()):
            self.bands_list.InsertItem(i, band.upper())
            self.bands_list.SetItem(i, 1, times['day'])
            self.bands_list.SetItem(i, 2, times['night'])
        
        self.vhf_list.DeleteAllItems()
        for i, (phen, val) in enumerate(vhf_data):
            self.vhf_list.InsertItem(i, phen)
            self.vhf_list.SetItem(i, 1, val)
        
        # Установить фокус на notebook (на первой вкладке)
        self.notebook.SetSelection(0)
        self.notebook.SetFocus()
        
        # Звуковое уведомление об обновлении
        wx.Bell()
        # Включить кнопку обратно
        self.refresh_btn.Enable()

    def show_error(self, error_msg):
        wx.MessageBox(f"Ошибка загрузки данных: {error_msg}", "Ошибка", wx.OK | wx.ICON_ERROR)
        self.refresh_btn.Enable()

    def on_refresh(self, event):
        # Отключить кнопку во время загрузки
        self.refresh_btn.Disable()
        is_manual = event is not None
        threading.Thread(target=self.load_data, args=(is_manual,)).start()

if __name__ == '__main__':
    app = wx.App()
    SolarApp()
    app.MainLoop()