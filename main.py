import wx
import requests
import xml.etree.ElementTree as ET
import threading

class SolarApp(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title='Монитор радиопрохождения R1BQE', size=(800, 650))
        self.panel = wx.Panel(self)
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook = wx.Notebook(self.panel)
        
        # Первая вкладка: Индексы
        self.indexes_panel = wx.Panel(self.notebook)
        self.indexes_sizer = wx.BoxSizer(wx.VERTICAL)
        self.list_ctrl = wx.ListCtrl(self.indexes_panel, style=wx.LC_REPORT | wx.BORDER_SUNKEN)
        self.list_ctrl.InsertColumn(0, 'Параметр', width=180)
        self.list_ctrl.InsertColumn(1, 'Значение', width=120)
        self.desc_col_width = 450
        self.list_ctrl.InsertColumn(2, 'Описание для радиолюбителя', width=self.desc_col_width)
        
        self.indexes_sizer.Add(self.list_ctrl, 1, wx.ALL | wx.EXPAND, 10)
        self.indexes_panel.SetSizer(self.indexes_sizer)
        self.notebook.AddPage(self.indexes_panel, 'Солнечные индексы')
        
        # Вторая вкладка: КВ
        self.bands_panel = wx.Panel(self.notebook)
        self.bands_sizer = wx.BoxSizer(wx.VERTICAL)
        self.bands_list = wx.ListCtrl(self.bands_panel, style=wx.LC_REPORT | wx.BORDER_SUNKEN)
        self.bands_list.InsertColumn(0, 'Диапазон', width=120)
        self.bands_list.InsertColumn(1, 'Днём', width=150)
        self.bands_list.InsertColumn(2, 'Ночью', width=150)
        self.bands_sizer.Add(self.bands_list, 1, wx.ALL | wx.EXPAND, 10)
        self.bands_panel.SetSizer(self.bands_sizer)
        self.notebook.AddPage(self.bands_panel, 'КВ Диапазоны')
        
        # Третья вкладка: УКВ
        self.vhf_panel = wx.Panel(self.notebook)
        self.vhf_sizer = wx.BoxSizer(wx.VERTICAL)
        self.vhf_list = wx.ListCtrl(self.vhf_panel, style=wx.LC_REPORT | wx.BORDER_SUNKEN)
        self.vhf_list.InsertColumn(0, 'Феномен (Регион)', width=400)
        self.vhf_list.InsertColumn(1, 'Состояние', width=150)
        self.vhf_sizer.Add(self.vhf_list, 1, wx.ALL | wx.EXPAND, 10)
        self.vhf_panel.SetSizer(self.vhf_sizer)
        self.notebook.AddPage(self.vhf_panel, 'УКВ Условия')
        
        # Кнопка обновления
        self.refresh_btn = wx.Button(self.panel, label='Обновить данные (F5)')
        self.refresh_btn.Bind(wx.EVT_BUTTON, self.on_refresh)
        
        # Галочка скрытия подсказок
        self.show_help_cb = wx.CheckBox(self.panel, label='Показывать подробные описания параметров')
        self.show_help_cb.SetValue(True)
        self.show_help_cb.Bind(wx.EVT_CHECKBOX, self.on_toggle_help)
        
        # Горячие клавиши
        accel_tbl = wx.AcceleratorTable([
            (wx.ACCEL_NORMAL, wx.WXK_F5, self.refresh_btn.GetId())
        ])
        self.SetAcceleratorTable(accel_tbl)
        
        self.sizer.Add(self.notebook, 1, wx.ALL | wx.EXPAND, 10)
        self.sizer.Add(self.refresh_btn, 0, wx.ALL | wx.CENTER, 5)
        self.sizer.Add(self.show_help_cb, 0, wx.ALL | wx.CENTER, 10)
        
        self.panel.SetSizer(self.sizer)
        self.current_params = [] 
        self.on_refresh(None)
        self.Show()

    def on_toggle_help(self, event):
        show = self.show_help_cb.GetValue()
        if show:
            self.list_ctrl.InsertColumn(2, 'Описание для радиолюбителя', width=self.desc_col_width)
        else:
            self.list_ctrl.DeleteColumn(2)
        if self.current_params:
            self.refresh_indexes_list()

    def get_k_desc(self, k):
        try:
            k = int(k)
            if k <= 1: return "Очень спокойно"
            if k <= 3: return "Спокойно"
            if k == 4: return "Нестабильно"
            return "Магнитная буря!"
        except: return ""

    def translate_val(self, val):
        trans = {
            'Poor': 'Плохо', 'Fair': 'Средне', 'Good': 'Хорошо', 'Excellent': 'Отлично',
            'Band Closed': 'Закрыт', 'Band Open': 'Открыт', 'VR QUIET': 'Очень спокойно',
            'QUIET': 'Спокойно', 'UNSETTLED': 'Неустойчиво', 'ACTIVE': 'Активно',
            'MINOR STORM': 'Малая буря', 'MAJOR STORM': 'Сильная буря', 'SEVERE STORM': 'Жесткий шторм'
        }
        return trans.get(val, val)

    def translate_vhf(self, name):
        trans = {
            'vhf-aurora': 'Аврора (отражение от полярного сияния)', 'E-Skip': 'Спорадик (E-слой)',
            'northern_hemi': 'Северное полушарие', 'europe': 'Европа', 'north_america': 'Северная Америка',
            'europe_6m': 'Европа 6м (50 МГц)', 'europe_4m': 'Европа 4м (70 МГц)'
        }
        return trans.get(name, name)

    def load_data(self, is_manual):
        url = 'https://www.hamqsl.com/solarxml.php'
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            data = root.find('solardata')
            
            def get_t(tag):
                t = data.findtext(tag)
                if tag == "updated":
                    import re
                    t = re.sub(r'(\d{2})(\d{2}) GMT$', r'\1:\2 GMT', t)
                return t if t and t != "NoRpt" else "нет данных"

            self.current_params = [
                ('Последнее обновление', get_t('updated'), 'Время последнего замера данных (GMT).'),
                ('SFI (Поток)', get_t('solarflux'), 'Индекс солнечного потока. Выше 150 — отлично для 10-15м.'),
                ('Sunspots (Пятна)', get_t('sunspots'), 'Чем больше пятен, тем лучше ионизация и выше частоты прохождения.'),
                ('A-Index', get_t('aindex'), 'Среднесуточная активность поля. Выше 15-20 — прохождение ухудшается.'),
                ('K-Index', f"{get_t('kindex')} ({self.get_k_desc(get_t('kindex'))})", 'Текущая активность. 0-2 — идеал, 4+ — замирания и шум.'),
                ('X-Ray (Всплески)', get_t('xray'), 'Интенсивность рентгена. Вспышки класса M или X «тушат» эфир.'),
                ('Magnetic Field (Bz)', get_t('magneticfield'), 'Вектор поля. Отрицательный Bz (ниже 0) открывает путь бурям.'),
                ('Solar Wind (Ветер)', f"{get_t('solarwind')} км/с", 'Норма: 300-450. Выше 500 — растет уровень шума.'),
                ('Proton Flux', get_t('protonflux'), 'Поток протонов. Выше 100 — закрываются полярные трассы.'),
                ('Electron Flux', get_t('electonflux'), 'Поток электронов. Выше 5000 — сильные фединги (замирания).'),
                ('Helium Line', get_t('heliumline'), 'Ионизация слоя F2. Хорошо, если значение выше 100.'),
                ('Aurora', get_t('aurora'), 'Уровень активности полярного сияния. Чем выше, тем хуже прохождение через полюса.'),
                ('LatDegree', f"{get_t('latdegree')}°", 'Граница сияния. Если ниже 60°, возможна Aurora в средних широтах.'),
                ('Geomag Field', self.translate_val(get_t('geomagfield')), 'Общий статус магнитного поля Земли.'),
                ('Signal Noise', get_t('signalnoise'), 'Уровень фонового шума по шкале S.'),
                ('MUF (МПЧ)', get_t('muf'), 'Максимально применимая частота. Выше этого значения — прохождения нет.'),
            ]
            
            bands_data = {}
            calc_cond = data.find('calculatedconditions')
            if calc_cond is not None:
                for band in calc_cond.findall('band'):
                    name, time, cond = band.get('name'), band.get('time'), band.text
                    if name not in bands_data: bands_data[name] = {'day': '—', 'night': '—'}
                    if cond: bands_data[name][time] = self.translate_val(cond.strip())
            
            vhf_data = []
            calc_vhf = data.find('calculatedvhfconditions')
            if calc_vhf is not None:
                for phen in calc_vhf.findall('phenomenon'):
                    name, loc, val = phen.get('name'), phen.get('location'), phen.text
                    if val:
                        label = f"{self.translate_vhf(name)} ({self.translate_vhf(loc)})"
                        vhf_data.append((label, self.translate_val(val.strip())))
            
            wx.CallAfter(self.update_ui, bands_data, vhf_data, get_t('updated'))
                
        except Exception as e:
            wx.CallAfter(self.show_error, str(e))

    def refresh_indexes_list(self):
        self.list_ctrl.DeleteAllItems()
        show_help = self.show_help_cb.GetValue()
        for i, (label, value, desc) in enumerate(self.current_params):
            self.list_ctrl.InsertItem(i, label)
            self.list_ctrl.SetItem(i, 1, str(value))
            if show_help:
                self.list_ctrl.SetItem(i, 2, desc)

    def update_ui(self, bands_data, vhf_data, updated_time):
        self.refresh_indexes_list()
        
        self.bands_list.DeleteAllItems()
        sorted_bands = sorted(bands_data.keys(), key=lambda x: int(x.replace('m','')) if x.replace('m','').isdigit() else 0, reverse=True)
        for i, band in enumerate(sorted_bands):
            times = bands_data[band]
            self.bands_list.InsertItem(i, band.upper())
            self.bands_list.SetItem(i, 1, times['day'])
            self.bands_list.SetItem(i, 2, times['night'])
        
        self.vhf_list.DeleteAllItems()
        for i, (phen, val) in enumerate(vhf_data):
            self.vhf_list.InsertItem(i, phen)
            self.vhf_list.SetItem(i, 1, val)
        
        wx.Bell()
        self.SetTitle(f"Монитор R1BQE - Обновлено в {updated_time}")
        self.refresh_btn.Enable()

    def show_error(self, error_msg):
        wx.MessageBox(f"Ошибка загрузки данных: {error_msg}", "Ошибка", wx.OK | wx.ICON_ERROR)
        self.refresh_btn.Enable()

    def on_refresh(self, event):
        self.refresh_btn.Disable()
        threading.Thread(target=self.load_data, args=(event is not None,)).start()

if __name__ == '__main__':
    app = wx.App()
    SolarApp()
    app.MainLoop()