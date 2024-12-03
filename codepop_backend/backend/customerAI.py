
from rest_framework.views import APIView
from .views import refund_order
from .models import Order, Revenue
from django.http import JsonResponse
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import re

# Load Flan-T5 model and tokenizer
tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-medium")
model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-medium")

class Chatbot(APIView):

    def post(self, request, *args, **kwargs):
        user_input = request.data.get("message", "")
        wrong_drink_phase = request.data.get("wrong_drink_phase")
        refund_phase = request.data.get("refund_phase")
        order_num = request.data.get("order_num")
        drink_nums = request.data.get("drink_nums")
        grounding_info = "you are a customer service agent, answer the following: "

        def wrongDrinkLogic (user_input, wrong_drink_phase, order_num, drink_nums):
            if "cancel" in user_input.lower():
                return JsonResponse({
                            "responses": "Ok, canceling... \nplease let me know how I can further help you!",
                            "wrong_drink_phase": "none",
                            "refund_phase": "none",
                            "order_num": "none",
                            "drink_nums": "none"
                            })
            match wrong_drink_phase:
                case "none":
                    return None
                case "init":
                    if "refund" in user_input.lower():
                        return JsonResponse({
                            "responses": "Please provide us with your order number to proceed with refund!",
                            "wrong_drink_phase": "none",
                            "refund_phase": "1",
                            "order_num": "none",
                            "drink_nums": "none"
                            })
                    elif "remade" in user_input.lower():
                        return JsonResponse({
                            "responses": "Please provide us with your order number to remake your drink!",
                            "wrong_drink_phase": "1",
                            "refund_phase": "none",
                            "order_num": "none",
                            "drink_nums": "none"
                            })
                    else:
                        return JsonResponse({
                            "responses": "I'm sorry please clearly state wether you want a refund for a drink or if you want a drink remade. \n\nIf you want to cancel this process please say cancel at any time!",
                            "wrong_drink_phase": "init",
                            "refund_phase": "init",
                            "order_num": "none",
                            "drink_nums": "none"
                            })
                case "1":
                    order_numbers = [int(num) for num in re.findall(r'\d+', user_input)]
                    if(len(order_numbers) != 1):
                        return JsonResponse({
                            "responses": "I'm sorry I couldn't find your order from that information! Please clearly enter a single order number! \n\nIf you want to cancel this process please say cancel at any time!",
                            "wrong_drink_phase": "1",
                            "refund_phase": "none",
                            "order_num": "none",
                            "drink_nums": "none"
                            })
                    else:
                        order = Order.objects.filter(OrderID = int(order_numbers[0])).first()
                        if not order:
                            return JsonResponse({
                            "responses": "I'm sorry that order doesn't exist. \n\nIf you want to cancel this process please say cancel at any time!",
                            "wrong_drink_phase": "1",
                            "refund_phase": "none",
                            "order_num": "none",
                            "drink_nums": "none"
                            })
                        else:
                            drinks = order.Drinks.all()
                            print(drinks)
                            drinks_info = ""
                            drink_ids = ""
                            counter = 1
                            for drink in drinks:
                                drinks_info = drinks_info + f"[{counter}]: Drink Name: {drink.Name}\n"
                                string_soda_used = ", ".join(drink.SodaUsed)
                                drinks_info = drinks_info + f"Soda Used: {string_soda_used}\n"
                                string_syrups = ", ".join(drink.SyrupsUsed)
                                drinks_info = drinks_info + f"Syrups: {string_syrups}\n"
                                string_add_ins = ", ".join(drink.AddIns)
                                drinks_info = drinks_info + f"Add ins: {string_add_ins}\n"
                                drinks_info = drinks_info + f"Price: ${drink.Price:.2f}\n\n"
                                counter = counter + 1
                                drink_ids = drink_ids + f"{drink.DrinkID}, "
                            print(drink_ids)
                            return JsonResponse({
                            "responses": "We found your order! Please tell us which drink(s) we can remake for you?\nif you want all drinks remade say \"all\"\n\n" + drinks_info + "If you want to cancel this process please say cancel at any time!",
                            "wrong_drink_phase": "2",
                            "refund_phase": "none",
                            "order_num": order_numbers[0],
                            "drink_nums": drink_ids
                            })
                case "2":
                    drink_numbers = [int(num) for num in re.findall(r'\d+', user_input)]
                    drink_list = drink_nums.split(", ")
                    if "all" in user_input.lower():
                        # Convert to integers, ignoring empty or invalid values
                        drink_list = [int(num) for num in drink_list if num.strip().isdigit()]
                        new_order = Order.objects.create(
                            OrderStatus='pending',
                            PaymentStatus='remade'
                        )

                        new_order.Drinks.add(drink_list)

                        new_order.save()
                        new_order_id = new_order.OrderID
                        return JsonResponse({
                            "responses": "Sucessfully started remaking order, please continute by saying \"I accept\".",
                            "wrong_drink_phase": "3",
                            "refund_phase": "none",
                            "order_num": new_order_id,
                            "drink_nums": drink_nums
                            })
                    elif len(drink_nums) == 0:
                        return JsonResponse({
                            "responses": "You didn't enter a valid drink number...\nplease try again! \n\nIf you want to cancel this process please say cancel at any time!",
                            "wrong_drink_phase": "2",
                            "refund_phase": "none",
                            "order_num": order_num,
                            "drink_nums": drink_nums
                            })
                    elif len(drink_numbers) > len(drink_list):
                        return JsonResponse({
                            "responses": "You entered too many drinks to remake...\nplease try again! \n\nIf you want to cancel this process please say cancel at any time!",
                            "wrong_drink_phase": "2",
                            "refund_phase": "none",
                            "order_num": order_num,
                            "drink_nums": drink_nums
                            })
                    else:
                        drinks_to_reorder = []
                        for drink in drink_numbers:
                            if drink > len(drink_list):
                                return JsonResponse({
                                    "responses": "One of the drinks entered was not in the list...\nplease try again! \n\nIf you want to cancel this process please say cancel at any time!",
                                    "wrong_drink_phase": "2",
                                    "refund_phase": "none",
                                    "order_num": order_num,
                                    "drink_nums": drink_nums
                                    })
                            else:
                                drinks_to_reorder.append(drink_list[drink-1])
        
                        new_order = Order.objects.create(
                            OrderStatus='pending',
                            PaymentStatus='remade'
                        )

                        new_order.Drinks.add(*drinks_to_reorder)

                        new_order.save()
                        new_order_id = new_order.OrderID
                        return JsonResponse({
                            "responses": "Sucessfully started remaking drinks, please continute by saying \"I accept\".",
                            "wrong_drink_phase": "3",
                            "refund_phase": "none",
                            "order_num": new_order_id,
                            "drink_nums": drink_nums
                            })
                case "3":
                    if "i accept" in user_input.lower():
                        return JsonResponse({
                            "responses": "Thank you! your drink will be remade shortly",
                            "wrong_drink_phase": "4",
                            "refund_phase": "none",
                            "order_num": order_num,
                            "drink_nums": "none"
                            })
                    else:
                        return JsonResponse({
                            "responses": "Sorry you must say \"I accept\" before we can finish remaking your drink(s) \n\nIf you want to cancel this process please say cancel at any time!",
                            "wrong_drink_phase": "3",
                            "refund_phase": "none",
                            "order_num": order_num,
                            "drink_nums": drink_nums
                            })
                case "4":
                    return None
                    



        def refundLogic (user_input, refund_phase, order_num, drink_nums):
            if "cancel" in user_input.lower():
                return JsonResponse({
                            "responses": "Ok, canceling... \nplease let me know how I can further help you!",
                            "wrong_drink_phase": "none",
                            "refund_phase": "none",
                            "order_num": "none",
                            "drink_nums": "none"
                            })
            match refund_phase:
                case "none":
                    return None
                case "init":
                    if "refund" in user_input.lower():
                        return JsonResponse({
                            "responses": "Please provide us with your order number to proceed with refund!",
                            "wrong_drink_phase": "none",
                            "refund_phase": "1",
                            "order_num": "none",
                            "drink_nums": "none"
                            })
                    elif "remade" in user_input.lower():
                        return JsonResponse({
                            "responses": "Please provide us with your order number to remake your drink!",
                            "wrong_drink_phase": "1",
                            "refund_phase": "none",
                            "order_num": "none",
                            "drink_nums": "none"
                            })
                    else:
                        return JsonResponse({
                            "responses": "I'm sorry please clearly state wether you want a refund for a drink or if you want a drink remade. \n\nIf you want to cancel this process please say cancel at any time!",
                            "wrong_drink_phase": "init",
                            "refund_phase": "init",
                            "order_num": "none",
                            "drink_nums": "none"
                            })
                case "1":
                    order_numbers = [int(num) for num in re.findall(r'\d+', user_input)]
                    if(len(order_numbers) != 1):
                        return JsonResponse({
                            "responses": "I'm sorry I couldn't find your order from that information! Please clearly enter a single order number! \n\nIf you want to cancel this process please say cancel at any time!",
                            "wrong_drink_phase": "none",
                            "refund_phase": "1",
                            "order_num": "none",
                            "drink_nums": "none"
                            })
                    else:
                        order = Order.objects.filter(OrderID = int(order_numbers[0])).first()
                        if not order:
                            return JsonResponse({
                            "responses": "I'm sorry that order doesn't exist. \n\nIf you want to cancel this process please say cancel at any time!",
                            "wrong_drink_phase": "none",
                            "refund_phase": "1",
                            "order_num": "none",
                            "drink_nums": "none"
                            })
                        else:
                            drinks = order.Drinks.all()
                            print(drinks)
                            drinks_info = ""
                            drink_ids = ""
                            counter = 1
                            for drink in drinks:
                                drinks_info = drinks_info + f"[{counter}]: Drink Name: {drink.Name}\n"
                                string_soda_used = ", ".join(drink.SodaUsed)
                                drinks_info = drinks_info + f"Soda Used: {string_soda_used}\n"
                                string_syrups = ", ".join(drink.SyrupsUsed)
                                drinks_info = drinks_info + f"Syrups: {string_syrups}\n"
                                string_add_ins = ", ".join(drink.AddIns)
                                drinks_info = drinks_info + f"Add ins: {string_add_ins}\n"
                                drinks_info = drinks_info + f"Price: ${drink.Price:.2f}\n\n"
                                counter = counter + 1
                                drink_ids = drink_ids + f"{drink.DrinkID}, "
                            print(drink_ids)
                            return JsonResponse({
                            "responses": "Is this the order you want refunded?\nConfirm by saying yes\n\n" + drinks_info + "If you want to cancel this process please say cancel at any time!",
                            "wrong_drink_phase": "none",
                            "refund_phase": "2",
                            "order_num": order_numbers[0],
                            "drink_nums": drink_ids
                            })
                case "2":
                    drink_numbers = [int(num) for num in re.findall(r'\d+', user_input)]
                    drink_list = drink_nums.split(", ")
                    if "yes" in user_input.lower():
                        order_to_refund = Order.objects.get(OrderID = order_num)
                        stripe_id = order_to_refund.StripeID
                        print(stripe_id)
                        refund_success = refund_order(stripe_id)
                        orderRevenue = Revenue.objects.get(OrderID = order_num)
                        orderRevenue.Refunded = True
                        orderRevenue.save()
                        if(refund_success):
                            return JsonResponse({
                                "responses": "Sucessfully started refund, please continute by saying \"I accept\".",
                                "wrong_drink_phase": "none",
                                "refund_phase": "3",
                                "order_num": order_num,
                                "drink_nums": drink_nums
                                })
                        else:
                            return JsonResponse({
                                "responses": "Sorry, There was a problem processing the refund. Please try again later!",
                                "wrong_drink_phase": "none",
                                "refund_phase": "2",
                                "order_num": order_num,
                                "drink_nums": drink_nums
                                })
                    else:
                        return JsonResponse({
                            "responses": "Please say yes to confirm this is the order you want to refund! \n\nIf you want to cancel this process please say cancel at any time!",
                            "wrong_drink_phase": "none",
                            "refund_phase": "2",
                            "order_num": order_num,
                            "drink_nums": drink_nums
                            })
                case "3":
                    if "i accept" in user_input.lower():
                        return JsonResponse({
                            "responses": "Thank you! your refund has been proccessed",
                            "wrong_drink_phase": "none",
                            "refund_phase": "4",
                            "order_num": order_num,
                            "drink_nums": "none"
                            })
                    else:
                        return JsonResponse({
                            "responses": "Sorry you must say \"I accept\" before we can finish the refund! \n\nIf you want to cancel this process please say cancel at any time!",
                            "wrong_drink_phase": "none",
                            "refund_phase": "3",
                            "order_num": order_num,
                            "drink_nums": drink_nums
                            })
                case "4":
                    return None
                    



        wrongDrinkResponse = wrongDrinkLogic(user_input, wrong_drink_phase, order_num, drink_nums)
        refundResponse = refundLogic(user_input, refund_phase, order_num, drink_nums)

        if(wrongDrinkResponse != None):
            return wrongDrinkResponse
        if(refundResponse != None):
            return refundResponse

        drink_made_wrong_keywords = [
            "wrong drink", "incorrect drink", "bad drink", "mistake", "not what I ordered",
            "off", "tastes wrong", "too sweet", "not sweet enough", "too bitter", "too sour",
            "too salty", "wrong flavor", "missing flavor", "added flavor", "wrong syrup",
            "extra syrup", "not enough syrup", "wrong base", "too much ice", "not enough ice",
            "flat", "warm", "cold", "too fizzy", "not fizzy", "wrong size", "wrong temperature",
            "messed up", "forgot ingredient", "overfilled", "underfilled", "weird taste",
            "unusual taste", "gross", "disgusting", "not fresh", "stale", "expired",
            "wrong toppings", "missing toppings", "extra toppings", "wrong ingredients",
            "bad mix", "not stirred", "too diluted", "watered down", "burnt taste",
            "sour taste", "bitter taste", "wrong sweetness", "too strong", "not strong enough",
            "wrong cream", "spoiled", "odd smell", "bad smell", "funky taste",
            "not as ordered", "doesn’t taste right", "off flavor", "odd aftertaste",
            "too creamy", "not creamy enough", "incorrect consistency", "too thick",
            "too thin", "strange consistency", "unpleasant aftertaste", "wrong texture",
            "wrong ratio", "overpowering flavor", "bland", "missing shot", "extra shot",
            "different drink", "wrong drink name", "unsatisfied", "not right", "mistaken order",
            "missing drink", "didn't receive drink", "forgot drink", "drink never arrived",
            "missing item", "order incomplete", "drink was left out", "never got my drink",
            "drink wasn’t included", "drink not in bag", "left out my drink", "didn’t deliver drink",
            "drink made wrong", "drink was made wrong", "drink is wrong", "drink is made wrong",
            "didn't get drink", "didn't get my drink", "didn't get a drink", "made wrong", "drink remade"
        ]

        refund_keywords = [
            "refund", "money back", "return my money", "get a refund", "compensation",
            "reimbursement", "want my money back", "give me my money", "credit", 
            "not satisfied", "not happy", "not worth it", "poor quality", "bad experience", 
            "unsatisfactory", "didn't like it", "request refund", "ask for refund", 
            "need a refund", "want a refund", "reimburse me", "return", "return policy",
            "customer service", "unacceptable", "demand a refund", "disappointed", 
            "unhappy with service", "refund request", "claim refund", "issue refund",
            "compensation for inconvenience", "unsatisfactory experience", 
            "unsatisfied with product", "exchange", "swap", "not as expected", 
            "didn’t meet expectations", "request money back", "money back guarantee",
            "seek reimbursement", "entitled to refund", "need compensation", 
            "request credit", "partial refund", "discount", "voucher", 
            "not worth the money", "not good value", "overcharged", "incorrect charge", 
            "wrong billing", "bad service", "inconvenienced", "request resolution"
        ]
        
         # Check if user request has to do with wanting a refund or wanting a drink remade.
        made_wrong_found = any(keyword in user_input.lower() for keyword in drink_made_wrong_keywords)
        refund_keyword_found = any(keyword in user_input.lower() for keyword in refund_keywords)
        
        if(made_wrong_found or refund_keyword_found):
            print("drink made wrong or refund requested")
            return JsonResponse({
                "responses": "Oh no, I'm sorry that happend to you. To confirm do you want the drink remade or do you want a refund?",
                "wrong_drink_phase": "init",
                "refund_phase": "init",
                "order_num": "none",
                "drink_nums": "none"
                })

        full_input = grounding_info + user_input

        # encode the new user input, add the eos_token and return a tensor in Pytorch
        new_user_input_ids = tokenizer.encode(user_input + tokenizer.eos_token, return_tensors='pt')
        attention_mask = torch.ones_like(new_user_input_ids)

        # append the new user input tokens to the chat history
        bot_input_ids =  new_user_input_ids

        # generated a response while limiting the total chat history to 1000 tokens, 
        chat_history_ids = model.generate(bot_input_ids, 
                                          max_length=1000, 
                                          pad_token_id=tokenizer.eos_token_id, 
                                          temperature = 1.0, 
                                          top_k=50,
                                          do_sample=True,
                                          attention_mask = attention_mask,
                                          top_p=0.9,)
        

        # Decode and print the response
        response = tokenizer.decode(chat_history_ids[:, bot_input_ids.shape[-1]:][0], skip_special_tokens=True)
        print("Model response:", response)

        return JsonResponse({
            "responses": [response], 
            "wrong_drink_phase": "none", 
            "refund_phase":"none",
            "order_num": "none",
            "drink_nums": "none"})
    