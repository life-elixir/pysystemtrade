from copy import copy

from systems.subsystem import SubSystem
from systems.defaults import system_defaults
from syscore.objects import resolve_function, resolve_data_method, hasallattr, calc_or_cache_nested
from syscore.pdutils import apply_cap

class ForecastScaleCapFixed(SubSystem):
    """
    Create a SubSystem for scaling and capping forecasting
    
    This simple variation uses Fixed capping and scaling
    
    KEY INPUT: system.rules.get_raw_forecast(instrument_code, rule_variation_name)
                found in self.get_raw_forecast(instrument_code, rule_variation_name)
                
    KEY OUTPUT: system.forecastScaleCap.get_capped_forecast(instrument_code, rule_variation_name)

    Name: forecastScaleCap
    """
    
    
    def __init__(self, forecast_scalars=dict(), forecast_cap=None):
        """
        Create a SubSystem for scaling and capping forecasting
        
        Using Fixed capping and scaling
        
        :param forecast_scalars: Dict of forecast scalars, keynames trading_rule name
        :type trading_rules:    None     (will get scalars from self.parent.config.trading_rules...forecast_scalar)
                                dict  (will get scalars from passed dict)
        
        :param forecast_cap: Value to cap scaled forecasts at
        :type forecast_cap: None (will get cap from self.parent.config.parameters.forecast_cap, or from system defaults.py)
                            float
                            
        :returns: None
        
        """
        delete_on_recalc=["_forecast_scalars", "_scaled_forecast", "_forecast_cap", "_capped_forecast"]

        dont_delete=[]
        
        setattr(self, "_passed_forecast_scalars", forecast_scalars)
        setattr(self, "_passed_forecast_cap", forecast_cap)
        
        setattr(self, "_delete_on_recalc", delete_on_recalc)
        setattr(self, "_dont_recalc", dont_delete)

        setattr(self, "name", "forecastScaleCap")
    
    def get_raw_forecast(self, instrument_code, rule_variation_name):
        """
        Convenience method as we use the raw forecast several times
        
        KEY_INPUT

        :param instrument_code: 
        :type str: 
        
        :param rule_variation_name:
        :type str: name of the trading rule variation
        
        :returns: Tx1 pd.DataFrame, same size as forecast
        
        >>> from systems.provided.example.testdata import get_test_object_futures_with_rules
        >>> from systems.basesystem import System
        >>> (rules, rawdata, data, config)=get_test_object_futures_with_rules()
        >>> system=System([rawdata, rules, ForecastScaleCapFixed()], data, config)
        >>> system.forecastScaleCap.get_raw_forecast("EDOLLAR","ewmac8").tail(2)
                      ewmac8
        2015-04-21  1.082781
        2015-04-22  0.954941
        """

        raw_forecast=self.parent.rules.get_raw_forecast(instrument_code, rule_variation_name)
        
        return raw_forecast
    
    
    def get_forecast_scalar(self, instrument_code, rule_variation_name):
        """
        Get the scalar to apply to raw forecasts
    
        In this simple version it's the same for all instruments, and fixed

        We get the scalars from: (a) passed argument when this subsystem created
                                 (b) ... or if missing: configuration file in parent system
                                 (c) or if missing: uses the scalar from systems.defaults.py


        setattr(self, "_forecast_scalars", forecast_scalars)
        setattr(self, "_forecast_cap", forecast_cap)

        
        :param instrument_code: 
        :type str: 
        
        :param rule_variation_name:
        :type str: name of the trading rule variation
        
        :returns: float

        >>> from systems.provided.example.testdata import get_test_object_futures_with_rules
        >>> from systems.basesystem import System
        >>> (rules, rawdata, data, config)=get_test_object_futures_with_rules()
        >>> system1=System([rawdata, rules, ForecastScaleCapFixed()], data, config)
        >>>
        >>> ## From config
        >>> system1.forecastScaleCap.get_forecast_scalar("EDOLLAR", "ewmac8")
        5.3
        >>>
        >>> ## passed to subsystem
        >>> fsc=ForecastScaleCapFixed(forecast_scalars=dict(ewmac8=10.0))
        >>> system2=System([rawdata, rules, fsc], data, config)
        >>> system2.forecastScaleCap.get_forecast_scalar("EDOLLAR", "ewmac8")
        10.0
        >>>
        >>> ## default
        >>> unused=config.trading_rules['ewmac8'].pop('forecast_scalar')
        >>> system3=System([rawdata, rules, ForecastScaleCapFixed()], data, config)
        >>> system3.forecastScaleCap.get_forecast_scalar("EDOLLAR", "ewmac8")
        1.0
        """
        
        def _get_forecast_scalar(system,  instrument_code, rule_variation_name, this_subsystem):
            ## Try the subsystem stored argument
            if rule_variation_name in this_subsystem._passed_forecast_scalars:
                scalar=this_subsystem._passed_forecast_scalars[rule_variation_name]
            else:
                ## Try the config file
                    try:
                        scalar=system.config.trading_rules[rule_variation_name]['forecast_scalar']
                    except:
                        ## go with defaults
                        scalar=system_defaults['forecast_scalar']
        
            return scalar
        
        forecast_scalar=calc_or_cache_nested(self.parent, "_forecast_scalars", instrument_code, rule_variation_name, _get_forecast_scalar, self)

        return forecast_scalar
    
    def get_forecast_cap(self, instrument_code, rule_variation_name):
        """
        Get forecast cap
        
        In this simple version it's the same for all instruments, and rule variations
        
        We get the cap from:     (a) passed argument when this subsystem created
                                 (b) ... or if missing: configuration file in parent system
                                 (c) or if missing: uses the forecast_cap from systems.default.py
        
        :param instrument_code: 
        :type str: 
        
        :param rule_variation_name:
        :type str: name of the trading rule variation
        
        :returns: float

        >>> from systems.provided.example.testdata import get_test_object_futures_with_rules
        >>> from systems.basesystem import System
        >>> (rules, rawdata, data, config)=get_test_object_futures_with_rules()
        >>> system=System([rawdata, rules, ForecastScaleCapFixed()], data, config)
        >>>
        >>> ## From config
        >>> system.forecastScaleCap.get_forecast_cap("EDOLLAR", "ewmac8")
        21.0
        >>>
        >>> ## passed to subsystem
        >>> system2=System([rawdata, rules, ForecastScaleCapFixed(forecast_cap=2.0)], data, config)
        >>> system2.forecastScaleCap.get_forecast_cap("EDOLLAR", "ewmac8")
        2.0
        >>>
        >>> ## default
        >>> unused=config.parameters.pop('forecast_cap')
        >>> system3=System([rawdata, rules, ForecastScaleCapFixed()], data, config)
        >>> system3.forecastScaleCap.get_forecast_cap("EDOLLAR", "ewmac8")
        20.0

        """

        def _get_forecast_cap(system,  instrument_code, rule_variation_name, this_subsystem):
            ## Try the subsystem stored argument
            if this_subsystem._passed_forecast_cap is not None:
                cap=this_subsystem._passed_forecast_cap
            else:
                ## Try the config file
                    try:
                        cap=system.config.parameters['forecast_cap']
                    except:
                        ## go with defaults
                        cap=system_defaults['forecast_cap']
        
            return cap
        
        forecast_cap=calc_or_cache_nested(self.parent, "_forecast_cap", instrument_code, rule_variation_name, _get_forecast_cap, self)

        return forecast_cap

    
    def get_scaled_forecast(self, instrument_code, rule_variation_name):
        """
        Return the scaled forecast
        
        :param instrument_code: 
        :type str: 
        
        :param rule_variation_name:
        :type str: name of the trading rule variation
        
        :returns: Tx1 pd.DataFrame, same size as forecast

        >>> from systems.provided.example.testdata import get_test_object_futures_with_rules
        >>> from systems.basesystem import System
        >>> (rules, rawdata, data, config)=get_test_object_futures_with_rules()
        >>> system=System([rawdata, rules, ForecastScaleCapFixed()], data, config)
        >>> system.forecastScaleCap.get_scaled_forecast("EDOLLAR", "ewmac8").tail(2)
                      ewmac8
        2015-04-21  5.738741
        2015-04-22  5.061187
        """
        
        def _get_scaled_forecast(system,  instrument_code, rule_variation_name, this_subsystem):
            raw_forecast=this_subsystem.get_raw_forecast(instrument_code, rule_variation_name)
            scale=this_subsystem.get_forecast_scalar(instrument_code, rule_variation_name)
            
            scaled_forecast=raw_forecast*scale
            
            return scaled_forecast
        
        scaled_forecast=calc_or_cache_nested(self.parent, "_scaled_forecast", instrument_code, rule_variation_name, _get_scaled_forecast, self)

        return scaled_forecast

    def get_capped_forecast(self, instrument_code, rule_variation_name):
        """

        Return the capped, scaled,  forecast

        KEY OUTPUT

        
        :param instrument_code: 
        :type str: 
        
        :param rule_variation_name:
        :type str: name of the trading rule variation
        
        :returns: Tx1 pd.DataFrame, same size as forecast

        >>> from systems.provided.example.testdata import get_test_object_futures_with_rules
        >>> from systems.basesystem import System
        >>> (rules, rawdata, data, config)=get_test_object_futures_with_rules()
        >>> system=System([rawdata, rules, ForecastScaleCapFixed(forecast_cap=4.0)], data, config)
        >>> system.forecastScaleCap.get_capped_forecast("EDOLLAR", "ewmac8").tail(2)
                    ewmac8
        2015-04-21       4
        2015-04-22       4
        
        
        """
        
        def _get_capped_forecast(system,  instrument_code, rule_variation_name, this_subsystem):
            
            scaled_forecast=this_subsystem.get_scaled_forecast(instrument_code, rule_variation_name)
            cap=this_subsystem.get_forecast_cap(instrument_code, rule_variation_name)
            
            capped_forecast=apply_cap(scaled_forecast, cap)
            capped_forecast.columns=scaled_forecast.columns
            
            return capped_forecast
        
        capped_forecast=calc_or_cache_nested(self.parent, "_capped_forecast", instrument_code, rule_variation_name, _get_capped_forecast, self)

        return capped_forecast

    
if __name__ == '__main__':
    import doctest
    doctest.testmod()