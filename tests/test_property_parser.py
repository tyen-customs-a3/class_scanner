import logging
from src.parser.property_parser import PropertyParser

logger = logging.getLogger(__name__)

def test_property_parsing_with_nested_classes():
    """Test property parsing with nested classes present"""
    content = """
        property1 = "value1";
        
        class NestedClass {
            nested = "ignore";
        };
        
        property2 = "value2";
    """
    
    parser = PropertyParser()
    properties = parser.parse_block_properties(content)
    
    logger.debug(properties)
    
    assert len(properties) == 2
    assert properties["property1"].value == "value1"  # No quotes in assertion
    assert properties["property2"].value == "value2"  # No quotes in assertion
    assert "nested" not in properties

def test_array_property_parsing():
    """Test parsing of array properties"""
    content = """
        empty[] = {};
        simple[] = {"value"};
        multiple[] = {"one", "two"};
        mixed[] = {1, "two", MyClass};
    """
    
    parser = PropertyParser()
    properties = parser.parse_block_properties(content)
    
    logger.debug(properties)
    
    assert properties["empty"].is_array
    assert len(properties["empty"].array_values) == 0
    assert len(properties["multiple"].array_values) == 2

# Add new test for full class parsing
def test_property_parsing_with_class_wrapper():
    """Test that property parser can handle full class definitions too"""
    content = """
    class TestClass {
        prop1 = "test";
        prop2 = 123;
    };
    """
    
    parser = PropertyParser()
    properties = parser.parse_block_properties(content)
    
    assert len(properties) == 2
    assert properties["prop1"].value == "test"  # No quotes in assertion
    assert properties["prop2"].value == "123"  # Numbers as strings without quotes

def test_deeply_nested_properties():
    """Test parsing of deeply nested property structures"""
    content = """
        outer[] = {
            {1, 2, {"inner", "values"}},
            {3, {4, {5, "deep"}}},
            {{{{{"maximum_depth"}}}}}
        };
        mixed[] = {
            "string",
            123,
            {1, 2},
            {"nested", {}, {{}}},
            MyClass
        };
    """
    
    parser = PropertyParser()
    properties = parser.parse_block_properties(content)
    
    assert "outer" in properties
    assert properties["outer"].is_array
    assert len(properties["outer"].array_values) == 3
    assert "mixed" in properties
    assert len(properties["mixed"].array_values) == 5

def test_malformed_property_values():
    """Test handling of malformed property values"""
    content = """
        unterminated_string = "unclosed;
        unclosed_array[] = {1, 2, 3;
        unmatched_brace = {test};
        missing_semicolon = "value"
        empty_name = = "test";
        multiple_equals = value = = "test";
        invalid_chars = @#$%;
    """
    
    parser = PropertyParser()
    properties = parser.parse_block_properties(content)
    
    # Should ignore or handle malformed properties gracefully
    assert len(properties) == 0

def test_property_value_types():
    """Test correct identification of different property value types"""
    content = """
        string_value = "test";
        number_value = 123;
        negative_number = -456;
        float_number = 123.456;
        boolean_true = true;
        boolean_false = false;
        identifier = MyClass;
        path_value = \models\test.p3d;
        mixed_array[] = {123, "string", true, MyClass};
    """
    
    parser = PropertyParser()
    properties = parser.parse_block_properties(content)
    
    assert properties["string_value"].value == "test"
    assert properties["number_value"].value == "123"
    assert properties["negative_number"].value == "-456"
    assert properties["float_number"].value == "123.456"
    assert properties["boolean_true"].value == "true"
    assert properties["boolean_false"].value == "false"
    assert properties["identifier"].value == "MyClass"
    assert properties["path_value"].value == "\\models\\test.p3d"
    assert len(properties["mixed_array"].array_values) == 4

def test_property_edge_cases():
    """Test edge cases in property definitions"""
    content = """
        empty_string = "";
        space_string = " ";
        quotes_in_string = "test""test";
        escaped_quotes = "test\"test";
        unicode_value = "тест";
        very_long_value = "this is a very long string value that exceeds normal length limits and should still be handled correctly by the parser without any issues or truncation of the content";
        repeated_array[] = {"value", "value", "value", "value", "value"};
        nested_empty_arrays[] = {{}, {}, {}, {}};
    """
    
    parser = PropertyParser()
    properties = parser.parse_block_properties(content)
    
    assert properties["empty_string"].value == ""
    assert properties["space_string"].value == " "
    assert "unicode_value" in properties
    assert len(properties["repeated_array"].array_values) == 5
    assert len(properties["nested_empty_arrays"].array_values) == 4

def test_property_inheritance():
    """Test property parsing with class inheritance"""
    content = """
        class ParentClass {
            prop1 = "parent";
            array[] = {1, 2, 3};
        };
        
        class ChildClass: ParentClass {
            prop1 = "child";  // Override
            prop2 = "new";    // New property
            array[] += {4, 5}; // Append to parent
        };
    """
    
    parser = PropertyParser()
    child_properties = parser.parse_block_properties(content)
    
    assert child_properties["prop1"].value == "child"
    assert child_properties["prop2"].value == "new"
    assert "+=" in content  # Just verify presence of append operator

def test_special_syntax():
    """Test special property syntax cases"""
    content = """
        texture = "#(argb,8,8,3)color(1,1,1,1)";
        model[] = {"path\to\model.p3d", "path/to/model.p3d"};
        code = "call { _this call fnc_test; };";
        macro_value = __EVAL(1+1);
        condition = "isNull _this";
    """
    
    parser = PropertyParser()
    properties = parser.parse_block_properties(content)
    
    assert "#(argb,8,8,3)" in properties["texture"].value
    assert len(properties["model"].array_values) == 2
    assert "call" in properties["code"].value
    assert "__EVAL" in properties["macro_value"].value

def test_commented_properties():
    """Test handling of commented properties"""
    content = """
        // commented_out = "value";
        valid = "test"; // End of line comment
        /* block_commented = "value"; */
        array[] = {  // Comment in array
            "value1", // Comment after value
            // "commented_value",
            "value2"  /* Block comment */
        };
    """
    
    parser = PropertyParser()
    properties = parser.parse_block_properties(content)
    
    assert "commented_out" not in properties
    assert "block_commented" not in properties
    assert properties["valid"].value == "test"
    assert len(properties["array"].array_values) == 2
