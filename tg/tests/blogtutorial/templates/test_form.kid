<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#">

  <head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <title>Welcome to PyGears!!!</title>
  </head>
  
  <body>
    
    <h1>Welcome to PyGears!!!</h1>

    <form method="POST" action="sub/do_test">
      A: <input name="a" value="${h.value_for('a')}"/>
      ${h.error_for('a')}
    </form>

  </body>
</html>