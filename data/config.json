{
  "Sheets": [
    {
      "Name": "Consumption (Invoice_Hist)",
      "NameExpression": "(?i)consumption",
      "Variable": "Consumption_Invoice_Hist",
      "Errors": [],
      "Data": "",
      "Columns": [
        {
          "Name": "Plant Name",
          "AlternateNames": [
            "Country"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Plant Code",
          "AlternateNames": [
            "Plant"
          ],
          "NameExpression": "",
          "DataExpression": "(?i)^[A-Z][0-9]+$",
          "CustomExpressionError": "Value must match PlantCode format. Example A350",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "RM Code",
          "AlternateNames": [
            "Material Code"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "RM Name",
          "AlternateNames": [
            "Material Desc"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Movement Type",
          "AlternateNames": [
            "Mvt Type"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Post Date",
          "AlternateNames": [
            "Posting Date"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "DataType": "DateTime",
          "CustomExpressionError": "Value must be a Date in DD/MM/YYYY format",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Post Week",
          "AlternateNames": [
            "Week/Year"
          ],
          "NameExpression": "",
          "DataExpression": "^(0?[1-9]|[1-4][0-9]|5[0-3])\\.(\\d{4})$",
          "DataType": "float",
          "CustomExpressionError": "Value must match Week.Year format. Example 32.2024",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Movement Qty",
          "AlternateNames": [
            "Invoice (Units)"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "float",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        }
      ]
    },
    {
      "Name": "BOM (Forecast_Data History)",
      "NameExpression": "(?=.*Historical)(?=.*Forecast)",
      "Variable": "BOM_Forecast_Data_History",
      "Errors": [],
      "Data": "",
      "Columns": [
        {
          "Name": "Plant Name",
          "AlternateNames": [
            "Country"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Plant Code",
          "AlternateNames": [
            "Plant"
          ],
          "NameExpression": "",
          "DataExpression": "(?i)^[A-Z][0-9]+$",
          "CustomExpressionError": "Value must match PlantCode format. Example A350",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "RM Code",
          "AlternateNames": [
            "Material Code"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "RM Name",
          "AlternateNames": [
            "Material Desc"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Category",
          "AlternateNames": [
            "RM Class Group"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Source",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Cycle",
          "AlternateNames": [
            "Planning cycle"
          ],
          "NameExpression": "",
          "DataExpression": "\\b(30|60|90)\\b",
          "DataType": "int",
          "CustomExpressionError": "Value must be either 30, 60 or 90",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "",
          "AlternateNames": [],
          "NameExpression": "^(20\\d{2})(0[1-9]|1[0-2])$",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "float",
          "Required": true,
          "RepeatNumber": 12,
          "Errors": []
        }
      ]
    },
    {
      "Name": "BOM (Forecast_Data Future)",
      "NameExpression": "(?i)6m.*forecast|forecast.*6m",
      "Variable": "BOM_Forecast_Data_Future",
      "Errors": [],
      "Data": "",
      "Columns": [
        {
          "Name": "Plant Name",
          "AlternateNames": [
            "Country"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Plant Code",
          "AlternateNames": [
            "Plant"
          ],
          "NameExpression": "",
          "DataExpression": "(?i)^[A-Z][0-9]+$",
          "CustomExpressionError": "Value must match PlantCode format. Example A350",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "RM Code",
          "AlternateNames": [
            "Material Code"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "RM Name",
          "AlternateNames": [
            "Material Desc"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": false,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Category",
          "AlternateNames": [
            "RM Class Group"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Source",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Cycle",
          "AlternateNames": [
            "Planning cycle"
          ],
          "NameExpression": "",
          "DataExpression": "\\b(30|60|90)\\b",
          "CustomExpressionError": "Only values of 30, 60, or 90 are acceptable.",
          "DataType": "int",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "",
          "AlternateNames": [],
          "NameExpression": "^(20\\d{2})(0[1-9]|1[0-2])$",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "float",
          "Required": true,
          "RepeatNumber": 6,
          "Errors": []
        }
      ]
    },
    {
      "Name": "Supply_Parameters",
      "NameExpression": "(?i)(supply).*?(parameter[s]?)",
      "Variable": "Supply_Parameters",
      "Errors": [],
      "Data": "",
      "Columns": [
        {
          "Name": "Region",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "PLANT",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Plant Code",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "(?i)^[A-Z][0-9]+$",
          "CustomExpressionError": "Value must match PlantCode format. Example A350",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Material Code",
          "AlternateNames": [
            "RM Code"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Material Desc",
          "AlternateNames": [
            "RM DESCRIPTION",
            "RM Name"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": false,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Supplier Code",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Supplier Name",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "SOB",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "float",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "INCO Term",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Category",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "RM Type",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "(?i)^(Imported|Local\\s?\\(Imported\\)|Local)$",
          "CustomExpressionError": "Value must be either Local, Local(Imported) or Imported",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "RM Class Group",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Source Country",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Source Region",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "MINIMUM ORDER QTY (Units)",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "float",
          "Required": false,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Supply Reliability (%)",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "float",
          "Required": false,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Information Cycle (Days)",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": false,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Service Level (%)",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "float",
          "Required": false,
          "RepeatNumber": 0,
          "Errors": []
        }
      ]
    },
    {
      "Name": "Sourcing_Data",
      "NameExpression": "(?i)(sourcing).*?(data)",
      "Variable": "Sourcing_Data",
      "Errors": [],
      "Data": "",
      "Columns": [
        {
          "Name": "Country",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Additional Time (Days)",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": false,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Plant Code",
          "AlternateNames": [
            "Plant"
          ],
          "NameExpression": "",
          "DataExpression": "(?i)^[A-Z][0-9]+$",
          "CustomExpressionError": "Value must match PlantCode format. Example A350",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "RM Code",
          "AlternateNames": [
            "Material Code"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "RM Name",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Supplier Code",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Supplier name",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Country of Origin",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Transit Time (Days)",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": false,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Transit Time Std. Dev. (%)",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "float",
          "Required": false,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Shipping Interval (Days)",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": false,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Shipping Interval Std. Dev. (%)",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "float",
          "Required": false,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Shipping Lot Size (Units)",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "float",
          "Required": false,
          "RepeatNumber": 0,
          "Errors": []
        }
      ]
    },
    {
      "Name": "Product Master",
      "NameExpression": "(?i)(product).*?(master)",
      "Variable": "Product_Master",
      "Errors": [],
      "Data": "",
      "Columns": [
        {
          "Name": "SKU",
          "AlternateNames": [
            "RM Code"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "SKU Description",
          "AlternateNames": [
            "RM DESCRIPTION"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Subclass",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Planning cycle",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "\\b(30|60|90)\\b",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "RM Segmentation",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": false,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "RM Class Group",
          "AlternateNames": [
            "Category"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "OE_SKU (Y/N)",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": false,
          "RepeatNumber": 0,
          "Errors": []
        }
      ]
    },
    {
      "Name": "SKU_Transition",
      "NameExpression": "(?i)(sku).*?(transition)",
      "Variable": "SKU_Transition",
      "Errors": [],
      "Data": "",
      "Columns": [
        {
          "Name": "Phase-Out RM Code",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Phase-In RM Code",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Plant Code",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "(?i)^[A-Z][0-9]+$",
          "CustomExpressionError": "Value must match PlantCode format. Example A350",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        }
      ]
    },
    {
      "Name": "Supplier_Transition",
      "NameExpression": "(?i)(supplier).*?(transition)",
      "Variable": "Supplier_Transition",
      "Errors": [],
      "Data": "",
      "Columns": [
        {
          "Name": "Phase-Out Supplier Code",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Phase-In Supplier Code",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Plant Code",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "(?i)^[A-Z][0-9]+$",
          "CustomExpressionError": "Value must match PlantCode format. Example A350",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        }
      ]
    },
    {
      "Name": "Actual Inventory",
      "NameExpression": "(?i)(actual|act).*?(inventory)",
      "Variable": "Actual_Inventory",
      "Errors": [],
      "Data": "",
      "Columns": [
        {
          "Name": "CODE",
          "AlternateNames": [
            "RM Code"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "DataType": "int",
          "CustomExpressionError": "",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "DESCRIPTION",
          "AlternateNames": [
            "RM DESCRIPTION"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Plant Code",
          "AlternateNames": [
            "Plant"
          ],
          "NameExpression": "",
          "DataExpression": "(?i)^[A-Z][0-9]+$",
          "CustomExpressionError": "Value must match PlantCode format. Example A350",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Classification",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "QTY",
          "AlternateNames": [
            "Inventory",
            "Quantity"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "float",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "MAP",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "float",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "VALUE",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "float",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        }
      ]
    },
    {
      "Name": "Shipping_Interval",
      "NameExpression": "(?i)(shipping).*?(interval)",
      "Variable": "Shipping_Interval",
      "Errors": [],
      "Data": "",
      "Columns": [
        {
          "Name": "Plant Name",
          "AlternateNames": [
            "Country"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Plant Code",
          "AlternateNames": [
            "Plant"
          ],
          "NameExpression": "",
          "DataExpression": "(?i)^[A-Z][0-9]+$",
          "CustomExpressionError": "Value must match PlantCode format. Example A350",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "RM Code",
          "AlternateNames": [
            "Material Code"
          ],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "RM Name",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Movement Type",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Post Date",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "DataType": "DateTime",
          "CustomExpressionError": "Value must be a Date in DD/MM/YYYY format",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Post Week",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "^(0?[1-9]|[1-4][0-9]|5[0-3])\\.(\\d{4})$",
          "DataType": "float",
          "CustomExpressionError": "Value must match Week.Year format. Example 32.2024",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Movement Qty",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "DataType": "float",
          "CustomExpressionError": "",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Supplier",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        }
      ]
    },
    {
      "Name": "Supply&Shipping_Var",
      "NameExpression": "(?i)(supply).*?(shipping).*?(var)",
      "Variable": "Supply&Shipping_Var",
      "Errors": [],
      "Data": "",
      "Columns": [
        {
          "Name": "PO #",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "DataType": "int",
          "CustomExpressionError": "",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Plant Code",
          "AlternateNames": [
            "Plant"
          ],
          "NameExpression": "",
          "DataExpression": "(?i)^[A-Z][0-9]+$",
          "CustomExpressionError": "Value must match PlantCode format. Example A350",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Material Code",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Material Name",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Country of Origin",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Supplier ETD (POL)",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "Value must be a Date in DD/MM/YYYY format",
          "DataType": "DateTime",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Port of Loading",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Latest ETD (POL)",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "Value must be a Date in DD/MM/YYYY format",
          "DataType": "DateTime",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "ATD (POL)",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "Value must be a Date in DD/MM/YYYY format",
          "DataType": "DateTime",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Supplier\nETA (POD)",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "Value must be a Date in DD/MM/YYYY format",
          "DataType": "DateTime",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Prev ETA (POD)\n02.28",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "(0[1-9]|[12][0-9]|3[01])-(0[1-9]|1[0-2])-\\d{4}",
          "CustomExpressionError": "",
          "DataType": "DateTime",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "ATA \n(POD)",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "(0[1-9]|[12][0-9]|3[01])-(0[1-9]|1[0-2])-\\d{4}",
          "CustomExpressionError": "",
          "DataType": "DateTime",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Destination\nPlant",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Supplier",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        }
      ]
    },
    {
      "Name": "Local_TT",
      "NameExpression": "(?i)(local).*?(tt)",
      "Variable": "Local_TT",
      "Errors": [],
      "Data": "",
      "Columns": [
        {
          "Name": "CODE",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "DataType": "int",
          "CustomExpressionError": "",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Plant Code",
          "AlternateNames": [
            "Plant"
          ],
          "NameExpression": "",
          "DataExpression": "(?i)^[A-Z][0-9]+$",
          "CustomExpressionError": "Value must match PlantCode format. Example A350",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "DESCRIPTION",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "str",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Transit Time",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Transit Time Std. Dev. (%)",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "float",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        },
        {
          "Name": "Supplier",
          "AlternateNames": [],
          "NameExpression": "",
          "DataExpression": "",
          "CustomExpressionError": "",
          "DataType": "int",
          "Required": true,
          "RepeatNumber": 0,
          "Errors": []
        }
      ]
    }
  ]
}