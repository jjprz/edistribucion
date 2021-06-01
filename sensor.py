import logging
from homeassistant.const import POWER_KILO_WATT, ENERGY_KILO_WATT_HOUR, CURRENCY_EURO
from homeassistant.helpers.entity import Entity
from .backend.EdistribucionAPI import Edistribucion
from .backend.EsiosAPI import Ree
from datetime import timedelta, date, datetime
import calendar, time

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=10)

festives = ['01-01', '06-01', '01-05', '12-10', '01-11', '06-12', '08-12', '25-12']

ss = ['01-04-2018', '21-04-2019', '12-04-2020', '04-04-2021', '17-04-2022', '09-04-2023', '31-03-2024', '20-04-2025', '05-04-2026', '28-03-2027',
      '16-04-2028', '01-04-2029', '21-04-2030', '13-04-2031', '28-03-2032', '17-04-2033', '09-04-2034', '25-03-2035', '13-04-2036', '05-04-2037',
      '25-04-2038', '10-04-2039', '01-04-2040', '21-04-2041', '06-04-2042', '29-03-2043', '17-04-2044', '09-04-2045', '25-03-2046', '14-04-2047',
      '05-04-2048', '18-04-2049', '10-04-2050', '02-04-2051', '21-04-2052', '06-04-2053', '29-03-2054', '18-04-2055', '02-04-2056', '22-04-2057']

def setup_platform(hass, config, add_entities, discovery_info=None):

    """Set up the sensor platform."""
    sensors = []

    edis = Edistribucion(config['username'],config['password'])
    edis.login()
    # r = edis.get_cups()
    # cups = r['data']['lstCups'][0]['Id']

    cont = edis.get_list_cups()[0]
    cups = cont['CUPS_Id']

    sensors.append(ConsumoNoFacturadoSensor(edis, cont))
    sensors.append(PrevisionFacturacionSensor(edis, cont))
    sensors.append(ContadorSensor(edis, cups))
    sensors.append(PotenciaMaximaSensor(edis, cups))
    add_entities(sensors)

class ContadorSensor(Entity):
    """Representation of a Sensor."""

    def __init__(self,edis,cups):
        """Initialize the sensor."""
        self._state = None
        self._attributes = {}
        self._edis = edis
        self._cups = cups
        self._icon = 'mdi:counter'
        self.entity_id = 'sensor.eds_contador'
        self.getAttrData()

    @property
    def name(self):
        """Return the name of the sensor."""
        return 'Contador'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return POWER_KILO_WATT

    @property
    def icon(self):
        """Return the icon to display."""
        return self._icon

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    def update(self):
        """Fetch new state data for the sensor."""
        self.getAttrData()

    def getAttrData(self):
        try:
            #Contador
            try:
                meter = self._edis.get_meter(self._cups)
            except:
                time.sleep(1)
                meter = self._edis.get_meter(self._cups)
                _LOGGER.exception('Zero fail to setup Contador e-distribución')

            attributes = {}
            attributes['Estado ICP'] = meter['data']['estadoICP']
            attributes['Totalizador'] = str(meter['data']['totalizador']).replace('.', '') + ' kWh'
            attributes['Porcentaje actual'] = meter['data']['percent'].replace('%', ' %')
            attributes['Potencia contratada'] = str(meter['data']['potenciaContratada']).replace('.', ',') + ' kW'
            self._state = meter['data']['potenciaActual']
            self._attributes = attributes
        except:
            _LOGGER.exception('Fail to setup Contador e-distribución')


class ConsumoNoFacturadoSensor(Entity):
    """Representation of a Sensor."""

    def __init__(self,edis,cont):
        """Initialize the sensor."""
        self._state = None
        self._attributes = {}
        self._icon = 'mdi:ev-station'
        self.entity_id = 'sensor.eds_consumo_no_facturado'
        self._edis = edis
        self._cont = cont
        self.getAttrData()

    @property
    def name(self):
        """Return the name of the sensor."""
        return 'Consumo no facturado'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return ENERGY_KILO_WATT_HOUR

    @property
    def icon(self):
        """Return the icon to display."""
        return self._icon

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    def update(self):
        """Fetch new state data for the sensor."""
        self.getAttrData()

    def getAttrData(self):
        try:
            #Consumo no facturado
            edis = self._edis
            cont = self._cont

            cycles = edis.get_list_cycles(cont)
            
            if len(cycles):
                lastCycle = cycles[0]['label'].split(" - ")[1]
                dStart = datetime.strptime(lastCycle, '%d/%m/%Y')
                dStart = dStart + timedelta(days=1)

            dEnd = datetime.today() - timedelta(days=1)
            sEnd = dEnd.strftime("%Y-%m-%d")
            #dStart = dEnd - timedelta(days=59)
            sStart = dStart.strftime("%Y-%m-%d")

            chart = edis.get_chart_points_by_range(cont, sStart, sEnd)
            
            consumoValle = consumoPunta = consumoLlana = 0.0
            dias = 0
            inicio = fin = horaInicio = horaFin = ''

            facturado = False

            if len(chart) and 'lstData' in chart['data']:
                for valueDay in chart['data']['lstData']:
                    now = datetime.strptime(valueDay[0]['date'], '%d/%m/%Y')
                    for valueHour in valueDay:
                        if valueHour['invoiced'] == facturado:
                            hour = int(valueHour['hour'][0:3])
                            if 'valueDouble' in valueHour:
                                dias += (1 / 24)
                                franja = self.get_franja(now, hour)
            
                                valueDouble = valueHour['valueDouble']

                                if franja == 'V':
                                    consumoValle += valueDouble
                                elif franja == 'L':
                                    consumoLlana += valueDouble
                                else:
                                    consumoPunta += valueDouble

                                hora = '{:02d}'.format(hour)
                                if inicio == '':
                                    inicio = valueHour['date']
                                    horaInicio = hora + ':00'
                                    
                                fin = valueHour['date']
                                horaFin = hora + ':59'
                            else:
                                break
            
                consumoTotal = consumoValle + consumoPunta + consumoLlana
                porcentajeValle = (consumoValle * 100) / consumoTotal
                consumoMedioDiario = consumoTotal / dias

                attributes = {}
                attributes['Consumo valle'] = str(round(consumoValle, 2)).replace('.', ',') + ' kWh'
                attributes['Consumo punta'] = str(round(consumoPunta, 2)).replace('.', ',') + ' kWh'
                attributes['Consumo llana'] = str(round(consumoLlana, 2)).replace('.', ',') + ' kWh'
                attributes['Porcentaje valle vs. punta / llana'] = str(round(porcentajeValle, 2)).replace('.', ',') + ' %'
                attributes['Fecha inicio'] = inicio + ' ' + horaInicio
                attributes['Fecha fin'] = fin + ' ' + horaFin
                #attributes['Días no facturados'] = str(dias) + ' días'
                attributes['Consumo medio diario'] = str(round(consumoMedioDiario, 2)).replace('.', ',') + ' kWh'
                self._state = round(consumoTotal, 2)
                self._attributes = attributes
            else:
                _LOGGER.warning('No data on Consumo no facturado e-distribución')
        except:
            _LOGGER.exception('Fail to setup Consumo no facturado e-distribución')

    def get_franja(self, now, hour):
        if hour < 8:
            return "V"
        elif now.weekday() >= 5 or self.is_festive(now):
            return "V"
        elif 10 <= hour < 14 or 18 <= hour < 22:
            return "P"
        else:
            return "L"

    def is_festive(self, now):
        if now.strftime("%d-%m") in festives:
            return True
        # elif (now - timedelta(days=5)).strftime("%d-%m-Y") in ss:
        #     return True
        else:
            return False

class PrevisionFacturacionSensor(Entity):
    """Representation of a Sensor."""

    def __init__(self,edis,cont):
        """Initialize the sensor."""
        self._state = None
        self._attributes = {}
        self._icon = 'mdi:file-chart-outline'
        self.entity_id = 'sensor.eds_prevision_facturacion'
        self._edis = edis
        self._cont = cont
        self.getAttrData()

    @property
    def name(self):
        """Return the name of the sensor."""
        return 'Previsión facturación'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return CURRENCY_EURO

    @property
    def icon(self):
        """Return the icon to display."""
        return self._icon

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    def update(self):
        """Fetch new state data for the sensor."""
        self.getAttrData()

    def getAttrData(self):
        try:
            #Previsión facturación
            ree = Ree()
            edis = self._edis
            cont = self._cont
            
            cycles = edis.get_list_cycles(cont)

            if len(cycles):
                lastCycle = cycles[0]['label'].split(" - ")[1]
                dStart = datetime.strptime(lastCycle, '%d/%m/%Y')
                dStart = dStart + timedelta(days=1)

            dEnd = datetime.today() - timedelta(days=1)
            sEnd = dEnd.strftime("%Y-%m-%d")
            #dStart = dEnd - timedelta(days=59)
            sStart = dStart.strftime("%Y-%m-%d")

            chart = edis.get_chart_points_by_range(cont, sStart, sEnd)

            consumoValle = consumoPunta = consumoLlana = 0.0
            precioValle = precioPunta = precioLlana = 0
            dias = 0
            inicio = None
            precios = {}

            facturado = False

            if len(chart) and 'lstData' in chart['data']:
                if chart['data']['lstData'][0][0]['invoiced']:
                    facturado = True

                for valueDay in chart['data']['lstData']:
                    c = 0
                    now = datetime.strptime(valueDay[0]['date'], '%d/%m/%Y')
                    precios = ree.get_prices(now)
                    for valueHour in valueDay:
                        if valueHour['invoiced'] == facturado:
                            hour = int(valueHour['hour'][0:3])
                            if 'valueDouble' in valueHour:
                                if not inicio:
                                    inicio = now
                                dias += (1 / 24)
                                franja = self.get_franja(now, hour)

                                valueDouble = valueHour['valueDouble']
                                if 'NOC' in precios[c]:
                                    precioX = (float(precios[c]['NOC'].replace(',','.')) / 1000) * valueDouble
                                else:
                                    precioX = (float(precios[c]['PCB'].replace(',','.')) / 1000) * valueDouble

                                if franja == 'V':
                                    consumoValle += valueDouble
                                    precioValle += precioX
                                elif franja == 'L':
                                    consumoLlana += valueDouble
                                    precioLlana += precioX
                                else:
                                    consumoPunta += valueDouble
                                    precioPunta += precioX
                            else:
                                break
                            
                            c += 1

                pot = self._cont['Power']
                PEAJE_ACCESO = 38.043426
                COSTES_COM = 3.113
                IMP_ELEC = 5.11269632
                ALQ_EQ = 0.026571

                #now = datetime.now()
                #daysMonth = calendar.monthrange(now.year, now.month)[1]
                #daysYear = 366 if calendar.isleap(now.year) else 365

                if facturado:
                    finPrev = now
                else:
                    finPrev = (inicio + timedelta(days=30))#.replace(day=14)

                delta = finPrev - inicio
                daysMonth = delta.days + 1
                daysYear = 366 if calendar.isleap(inicio.year) else 365

                peaje = (pot * PEAJE_ACCESO) * (dias / daysYear)
                fijo = (pot * COSTES_COM) * (dias / daysYear)

                subtotal = peaje + fijo + precioValle + precioPunta + precioLlana

                imp = subtotal * (IMP_ELEC / 100)
                alq = dias * ALQ_EQ
                subtotalOtros = imp + alq + subtotal
                
                total = subtotalOtros * 1.21

                #Previsión
                if dias > daysMonth:
                    daysMonth = dias

                precioVallePrev = (precioValle * daysMonth) / dias
                precioPuntaPrev = (precioPunta * daysMonth) / dias
                precioLlanaPrev = (precioLlana * daysMonth) / dias

                peajePrev = (pot * PEAJE_ACCESO) * (daysMonth / daysYear)
                fijoPrev = (pot * COSTES_COM) * (daysMonth / daysYear)

                subtotalPrev = (peajePrev + fijoPrev + precioVallePrev + precioPuntaPrev + precioLlanaPrev)

                impPrev = subtotalPrev * (IMP_ELEC / 100)
                alqPrev = daysMonth * ALQ_EQ
                subtotalOtrosPrev = impPrev + alqPrev + subtotalPrev

                totalPrev = subtotalOtrosPrev * 1.21

                consumoTotalPrev = (consumoValle + consumoPunta + consumoLlana) * daysMonth / dias

                attributes = {}
                if facturado:
                    attributes['Consumo total'] = str(round(consumoTotalPrev, 2)).replace('.', ',') + ' kWh'
                    attributes['Coste medio'] = '{:.2f}'.format(round(totalPrev / dias, 2)).replace('.', ',') + ' €'
                    attributes['Consumo medio'] = str(round(consumoTotalPrev / dias, 2)).replace('.', ',') + ' kWh'
                    attributes['Periodo'] = inicio.strftime('%d/%m/%Y') + ' - ' + finPrev.strftime('%d/%m/%Y')
                    attributes['Facturación'] = 'Cerrada'
                else:
                    attributes['Previsión consumo'] = str(round(consumoTotalPrev, 2)).replace('.', ',') + ' kWh'
                    attributes['Días previstos'] = str(daysMonth) + ' días'
                    attributes['Facturación actual'] = '{:.2f}'.format(round(total, 2)).replace('.', ',') + ' €'
                    attributes['Días reales'] = str('%g'%(round(dias,2))).replace('.', ',') + ' días'
                    attributes['Facturación'] = 'Abierta'
                self._state = round(totalPrev, 2)
                self._attributes = attributes
            else:
                _LOGGER.warning('No data on Previsión facturación e-distribución')
        except:
            _LOGGER.exception('Fail to setup Previsión facturación e-distribución')

    def get_franja(self, now, hour):
        if hour < 8:
            return "V"
        elif now.weekday() >= 5 or self.is_festive(now):
            return "V"
        elif 10 <= hour < 14 or 18 <= hour < 22:
            return "P"
        else:
            return "L"

    def is_festive(self, now):
        if now.strftime("%d-%m") in festives:
            return True
        # elif (now - timedelta(days=5)).strftime("%d-%m-Y") in ss:
        #     return True
        else:
            return False

class PotenciaMaximaSensor(Entity):
    """Representation of a Sensor."""

    def __init__(self,edis,cups):
        """Initialize the sensor."""
        self._state = None
        self._attributes = {}
        self._edis = edis
        self._cups = cups
        self._icon = 'mdi:chart-line'
        self.entity_id = 'sensor.eds_potencia_maxima'
        self.getAttrData()

    @property
    def name(self):
        """Return the name of the sensor."""
        return 'Potencia máxima registrada'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return POWER_KILO_WATT

    @property
    def icon(self):
        """Return the icon to display."""
        return self._icon

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    def update(self):
        """Fetch new state data for the sensor."""
        self.getAttrData()

    def getAttrData(self):
        try:
            #Potencias máximas
            maximeter = self._edis.get_maximeter_histogram(self._cups)
            listMax = []
            for maxi in maximeter['data']['lstData']:
                if maxi['value'] > 0:
                    max = {}
                    max['Fecha'] = maxi['date'].replace('-', '/')
                    max['Hora'] = maxi['hour']
                    max['Potencia'] = str(round(maxi['value'], 2)) + ' kW'
                    listMax.insert(0,max)

            attributes = {}
            for max in listMax:
                attributes[max['Fecha'][3:]] = max

            self._state = round(float(maximeter['data']['maxValue'][:5].replace(',', '.')), 2)
            self._attributes = attributes
        except:
            _LOGGER.exception('Fail to setup Potencia máxima e-distribución')
