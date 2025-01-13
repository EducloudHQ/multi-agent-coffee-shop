import aws_cdk as core
import aws_cdk.assertions as assertions

from coffee_order.coffee_order_stack import CoffeeOrderStack

# example tests. To run these tests, uncomment this file along with the example
# resource in coffee_order/coffee_order_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = CoffeeOrderStack(app, "coffee-order")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
