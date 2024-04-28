import java.time.Duration
import org.openqa.selenium.By
import org.openqa.selenium.firefox.FirefoxDriver
import org.openqa.selenium.support.ui.WebDriverWait
import sys.process._
import java.net._
import java.io._
import scala.collection.JavaConverters

object WillysGptDataScrapper {

  val folder = "data/"

  def downloadFile(url: String, destination: String): Unit = {
    (new URL(url) #> new File(destination)).!
    ()
  }

  def writeTxtFile(txt: String, destination: String): Unit = {
    val pw = new PrintWriter(new File(destination))
    pw.write(txt)
    pw.close
  }

  def cleanup(directory: String) = {
    val file = new File(directory)
    if (file.isDirectory) then
      file.listFiles.foreach(_.delete)
    else
      throw RuntimeException("folder is configured wrong")
  }

  def main(args: Array[String]): Unit = {
    System.setProperty(
      "webdriver.gecko.driver",
      "/opt/homebrew/bin/geckodriver"
    )
    val driver = new FirefoxDriver
    driver.manage.window.maximize()
    driver.manage.deleteAllCookies()
    driver.manage.timeouts.pageLoadTimeout(Duration.ofSeconds(40))
    driver.manage.timeouts.implicitlyWait(Duration.ofSeconds(30))
    driver.get("https://www.willys.se/anvandare/inloggning")

    cleanup(folder)

    Thread.sleep(3000)
    val declineCookies =
      driver.findElement(By.id("onetrust-reject-all-handler"))
    declineCookies.click()

    Thread.sleep(500)
    val userNameInput = driver.findElement(By.className("sc-827e1384-0"))
    userNameInput.sendKeys(System.getenv("WILLYS_USERNAME"))

    Thread.sleep(500)
    val passwordInput =
      driver.findElements(By.className("sc-827e1384-0")).get(1)
    passwordInput.sendKeys(System.getenv("WILLYS_PASSWORD"))

    Thread.sleep(1000)
    val login = driver.findElements(By.className("sc-dfa63f22-0")).get(1)
    // val login = driver.findElements(By.ByPartialLinkText("Logga in")).get(1)
    login.click()

    Thread.sleep(2000)
    val userId = driver.findElement(By.className("sc-a3164ebe-0"))
    val userName = userId.getText()
    writeTxtFile(userName, s"$folder/userName.txt")
    userId.click()

    Thread.sleep(500)
    val purchases = driver.findElement(By.ByPartialLinkText("Mina köp"))
    purchases.click()

    Thread.sleep(2000)

    val allPurchases = driver.findElements(By.className("sc-139d58d8-4"))
    val recieptLinks =
      for reciept <- JavaConverters.asScalaBuffer(allPurchases).toSeq
          inner = reciept.findElement(By.className("sc-f1f2eb33-0"))
      yield inner.getAttribute("href")
    
    for link <- recieptLinks
        params = new URI(link).getQuery.split('&').collect { case s"$key=$value" => key -> value }.toMap
        filePath = s"${folder}/${params("date")}-${params("storeId")}-${params("memberCardNumber")}.pdf"
      yield downloadFile(link, filePath)
 
    Thread.sleep(10000)
    driver.quit()
  }
}
