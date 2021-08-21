document.addEventListener('DOMContentLoaded', function()
{
    text = document.getElementById('footer-text')
    const possible_prompts = ["Aim to finish all your goals everyday. Even if you don't atleast you tried :)", "Remember that persistence makes all the difference", "It's never too late to pursue something new"]
    text.innerHTML = possible_prompts[Math.floor(Math.random() * possible_prompts.length)]

    setInterval(function(){
        document.getElementById("add_form").addEventListener("submit", function(event){
            event.preventDefault()
        });
    }, 3000);

});

// Try to figure out how to simply reload just the div with the information from database once any of the buttons are clicked 

function change_goal(todo_id)
{
    var form = $("#change_form_" + todo_id); 
    
    $.ajax({
        url: "/update/" + todo_id,
        type: "POST",
        cache: false,
        data: form.serialize(),
        success: function(){
            $(TODO).replaceWith(data)
        }
    })

}


function add_goal()
{
    var form = $("#add_form"); 
    $.ajax({
        url:"/add",
        type: "POST",
        data: form.serialize(),
        success: function(data){
            $(TODO).replaceWith(data)
        }
    })
    

}

function delete_goal(goal_id)
{
    $.ajax({
        url:"/delete/" + goal_id,
        type: "POST",
        dataType: "json",
        success: function(data){
            $(TODO).replaceWith(data)
        }
    })
}

function reload()
{
    $.ajax({
        url:"/reload",
        type: "POST",
        dataType: "json",
        success: function(data){
            console.log("success")
            alert("success")
            $(TODO).replaceWith(data)
        }
    })
}


